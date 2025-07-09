import pytest
import pandas as pd
from datetime import date, timedelta
from app.business_logic import (
    compute_quotes,
    deduplicate_payments,
    calculate_earned_per_policy,
    get_latest_policy_status,
    determine_eligibility,
    analyze_policies,
    calculate_agent_quotes,
    get_today
)
from app.config import config


class TestBasicFunctionality:
    """Test basic business logic functionality"""
    
    def test_basic_quote_calculation(self):
        """Test the basic quote calculation as in original test"""
        carrier = pd.DataFrame({
            "policy_id": ["P001", "P001"],
            "agent_id": ["A1", "A1"],
            "paid_date": ["2025-07-01", "2025-08-01"],
            "amount": [200.0, 200.0],
            "status": ["active", "active"],
            "carrier": ["Humana", "Humana"]
        })
        crm = pd.DataFrame({
            "policy_id": ["P001"],
            "agent_id": ["A1"],
            "submit_date": ["2025-06-15"],
            "ltv_expected": [800.0]
        })
        
        result = compute_quotes(carrier, crm)
        assert len(result) == 1
        assert result[0]["agent_id"] == "A1"
        assert result[0]["earned_to_date"] == 400.0  # 200 + 200
        expected_advance = (800.0 - 400.0) * config.ADVANCE_PERCENTAGE
        assert result[0]["safe_to_advance"] == expected_advance


class TestDuplicatePayments:
    """Test handling of duplicate payments"""
    
    def test_duplicate_payment_removal(self):
        """Test that duplicate payments are properly deduplicated"""
        carrier = pd.DataFrame({
            "policy_id": ["P001", "P001", "P002"],
            "agent_id": ["A1", "A1", "A1"],
            "paid_date": ["2025-07-01", "2025-07-01", "2025-07-02"],
            "amount": [200.0, 200.0, 150.0],
            "status": ["active", "active", "active"],
            "carrier": ["Humana", "Humana", "UHC"]
        })
        
        deduplicated = deduplicate_payments(carrier)
        assert len(deduplicated) == 2  # Should remove one duplicate
        
        # Check that unique entries remain
        unique_entries = deduplicated.groupby(['policy_id', 'paid_date', 'amount']).size()
        assert all(count == 1 for count in unique_entries)
    
    def test_duplicate_payments_in_quote_calculation(self):
        """Test edge case from sample data - PDUP1 policy with duplicate payments"""
        carrier = pd.DataFrame({
            "policy_id": ["PDUP1", "PDUP1"],
            "agent_id": ["A007", "A007"],
            "paid_date": ["2025-06-18", "2025-06-18"],
            "amount": [175.0, 175.0],
            "status": ["active", "active"],
            "carrier": ["UHC", "UHC"]
        })
        crm = pd.DataFrame({
            "policy_id": ["PDUP1"],
            "agent_id": ["A007"],
            "submit_date": ["2025-06-10"],
            "ltv_expected": [700.0]
        })
        
        result = compute_quotes(carrier, crm)
        assert len(result) == 1
        assert result[0]["earned_to_date"] == 175.0  # Only count once
        expected_advance = (700.0 - 175.0) * config.ADVANCE_PERCENTAGE
        assert result[0]["safe_to_advance"] == expected_advance


class TestClawBackScenarios:
    """Test handling of cancelled policies and claw-backs"""
    
    def test_claw_back_negative_payment(self):
        """Test claw-back scenario with negative payment"""
        carrier = pd.DataFrame({
            "policy_id": ["PCLAW1", "PCLAW1"],
            "agent_id": ["A005", "A005"],
            "paid_date": ["2025-06-17", "2025-07-07"],
            "amount": [200.0, -200.0],
            "status": ["active", "cancelled"],
            "carrier": ["Humana", "Humana"]
        })
        crm = pd.DataFrame({
            "policy_id": ["PCLAW1"],
            "agent_id": ["A005"],
            "submit_date": ["2025-06-05"],
            "ltv_expected": [800.0]
        })
        
        result = compute_quotes(carrier, crm)
        assert len(result) == 1
        assert result[0]["earned_to_date"] == 0.0  # 200 + (-200) = 0
        # Policy is cancelled, so not eligible for advance
        assert result[0]["safe_to_advance"] == 0.0
    
    def test_negative_earned_amount(self):
        """Test when claw-back exceeds original payments"""
        carrier = pd.DataFrame({
            "policy_id": ["P001"],
            "agent_id": ["A1"],
            "paid_date": ["2025-06-17"],
            "amount": [-500.0],  # Large claw-back
            "status": ["cancelled"],
            "carrier": ["Humana"]
        })
        crm = pd.DataFrame({
            "policy_id": ["P001"],
            "agent_id": ["A1"],
            "submit_date": ["2025-06-05"],
            "ltv_expected": [800.0]
        })
        
        result = compute_quotes(carrier, crm)
        assert len(result) == 1
        assert result[0]["earned_to_date"] == -500.0  # Negative earned amount
        # Remaining expected should be max(ltv_expected - earned, 0)
        # max(800 - (-500), 0) = 1300, but policy is cancelled so not eligible
        assert result[0]["safe_to_advance"] == 0.0


class TestPolicyStatusChanges:
    """Test retro policy status changes"""
    
    def test_latest_status_determination(self):
        """Test that latest status is used based on payment date"""
        carrier = pd.DataFrame({
            "policy_id": ["P001", "P001"],
            "agent_id": ["A1", "A1"],
            "paid_date": ["2025-06-15", "2025-07-01"],
            "amount": [200.0, 150.0],
            "status": ["active", "cancelled"],  # Status changed to cancelled
            "carrier": ["Humana", "Humana"]
        })
        
        latest_status = get_latest_policy_status(carrier)
        assert latest_status[("P001", "A1")] == "cancelled"
    
    def test_retro_status_change_affects_eligibility(self):
        """Test that retro status change affects eligibility"""
        carrier = pd.DataFrame({
            "policy_id": ["P001", "P001"],
            "agent_id": ["A1", "A1"],
            "paid_date": ["2025-06-15", "2025-07-01"],
            "amount": [200.0, 150.0],
            "status": ["active", "cancelled"],
            "carrier": ["Humana", "Humana"]
        })
        crm = pd.DataFrame({
            "policy_id": ["P001"],
            "agent_id": ["A1"],
            "submit_date": ["2025-06-05"],  # Old enough to be eligible
            "ltv_expected": [800.0]
        })
        
        result = compute_quotes(carrier, crm)
        assert len(result) == 1
        assert result[0]["earned_to_date"] == 350.0  # 200 + 150
        # Policy is cancelled (latest status), so not eligible
        assert result[0]["safe_to_advance"] == 0.0


class TestAdvanceCaps:
    """Test $2,000 cap scenarios"""
    
    def test_agent_exceeds_cap(self):
        """Test agent A001 exceeds $2,000 cap (from FAQ #10)"""
        # Create test data that would result in > $2000 advance
        carrier_data = []
        crm_data = []
        
        # Create multiple policies for agent A001 with high remaining values
        for i in range(10):
            policy_id = f"P{i:03d}"
            carrier_data.append({
                "policy_id": policy_id,
                "agent_id": "A001",
                "paid_date": "2025-06-15",
                "amount": 100.0,  # Small payment
                "status": "active",
                "carrier": "Humana"
            })
            crm_data.append({
                "policy_id": policy_id,
                "agent_id": "A001",
                "submit_date": "2025-06-01",  # Eligible date
                "ltv_expected": 1000.0  # High LTV
            })
        
        carrier = pd.DataFrame(carrier_data)
        crm = pd.DataFrame(crm_data)
        
        result = compute_quotes(carrier, crm)
        assert len(result) == 1
        assert result[0]["agent_id"] == "A001"
        # Should be capped at max advance amount
        assert result[0]["safe_to_advance"] == config.MAX_ADVANCE_AMOUNT
    
    def test_multiple_agents_individual_caps(self):
        """Test that cap is applied per agent individually"""
        carrier_data = []
        crm_data = []
        
        for agent_id in ["A001", "A002"]:
            for i in range(5):
                policy_id = f"P{agent_id[1:]}{i:02d}"
                carrier_data.append({
                    "policy_id": policy_id,
                    "agent_id": agent_id,
                    "paid_date": "2025-06-15",
                    "amount": 100.0,
                    "status": "active",
                    "carrier": "Humana"
                })
                crm_data.append({
                    "policy_id": policy_id,
                    "agent_id": agent_id,
                    "submit_date": "2025-06-01",
                    "ltv_expected": 1000.0
                })
        
        carrier = pd.DataFrame(carrier_data)
        crm = pd.DataFrame(crm_data)
        
        result = compute_quotes(carrier, crm)
        assert len(result) == 2
        
        # Both agents should hit the cap
        for quote in result:
            assert quote["safe_to_advance"] == config.MAX_ADVANCE_AMOUNT


class TestEligibilityRules:
    """Test policy eligibility rules"""
    
    def test_eligibility_date_requirement(self):
        """Test eligibility day requirement"""
        today = get_today()  # 2025-07-06
        
        # Policy submitted exactly eligibility_days ago should be eligible
        assert determine_eligibility(today - timedelta(days=config.ELIGIBILITY_DAYS), "active", today) == True
        
        # Policy submitted one day less than eligibility_days ago should not be eligible
        assert determine_eligibility(today - timedelta(days=config.ELIGIBILITY_DAYS-1), "active", today) == False
        
        # Policy submitted one day more than eligibility_days ago should be eligible
        assert determine_eligibility(today - timedelta(days=config.ELIGIBILITY_DAYS+1), "active", today) == True
    
    def test_late_payment_scenario(self):
        """Test PLATE1 - late payment scenario"""
        carrier = pd.DataFrame({
            "policy_id": ["PLATE1"],
            "agent_id": ["A010"],
            "paid_date": ["2025-08-15"],  # Future date
            "amount": [225.0],
            "status": ["active"],
            "carrier": ["Cigna"]
        })
        crm = pd.DataFrame({
            "policy_id": ["PLATE1"],
            "agent_id": ["A010"],
            "submit_date": ["2025-06-15"],  # Eligible submit date
            "ltv_expected": [900.0]
        })
        
        result = compute_quotes(carrier, crm)
        assert len(result) == 1
        # Payment is in the future, so earned_to_date should include it
        # (business logic doesn't filter by payment date)
        assert result[0]["earned_to_date"] == 225.0
        expected_advance = (900.0 - 225.0) * config.ADVANCE_PERCENTAGE
        assert result[0]["safe_to_advance"] == expected_advance


class TestEdgeCases:
    """Test various edge cases"""
    
    def test_no_payments_yet(self):
        """Test policy with no payments yet"""
        carrier = pd.DataFrame({
            "policy_id": [],
            "agent_id": [],
            "paid_date": [],
            "amount": [],
            "status": [],
            "carrier": []
        })
        crm = pd.DataFrame({
            "policy_id": ["P001"],
            "agent_id": ["A1"],
            "submit_date": ["2025-06-01"],
            "ltv_expected": [800.0]
        })
        
        result = compute_quotes(carrier, crm)
        assert len(result) == 1
        assert result[0]["earned_to_date"] == 0.0
        expected_advance = 800.0 * config.ADVANCE_PERCENTAGE
        assert result[0]["safe_to_advance"] == expected_advance
    
    def test_policy_fully_paid(self):
        """Test policy where earned exceeds LTV"""
        carrier = pd.DataFrame({
            "policy_id": ["P001"],
            "agent_id": ["A1"],
            "paid_date": ["2025-06-15"],
            "amount": [1000.0],  # More than LTV
            "status": ["active"],
            "carrier": ["Humana"]
        })
        crm = pd.DataFrame({
            "policy_id": ["P001"],
            "agent_id": ["A1"],
            "submit_date": ["2025-06-01"],
            "ltv_expected": [800.0]
        })
        
        result = compute_quotes(carrier, crm)
        assert len(result) == 1
        assert result[0]["earned_to_date"] == 1000.0
        # Remaining expected should be 0 (can't be negative)
        assert result[0]["safe_to_advance"] == 0.0
    
    def test_empty_datasets(self):
        """Test with empty datasets"""
        carrier = pd.DataFrame({
            "policy_id": [],
            "agent_id": [],
            "paid_date": [],
            "amount": [],
            "status": [],
            "carrier": []
        })
        crm = pd.DataFrame({
            "policy_id": [],
            "agent_id": [],
            "submit_date": [],
            "ltv_expected": []
        })
        
        result = compute_quotes(carrier, crm)
        assert len(result) == 0


class TestSampleDataScenarios:
    """Test with actual sample data scenarios"""
    
    def test_agent_a001_cap_scenario(self):
        """Test that agent A001 from sample data hits the $2,000 cap"""
        # This test simulates the FAQ #10 scenario
        # We'll create simplified data that represents agent A001's situation
        
        # Agent A001 has many policies with significant remaining values
        carrier_data = []
        crm_data = []
        
        # Simulate agent A001's high-value policies
        policies = [
            ("P00001", 150.0, 600.0, "2025-06-28"),
            ("P00002", 225.0, 900.0, "2025-06-16"),
            ("P00003", 175.0, 700.0, "2025-06-13"),
            ("P00004", 225.0, 900.0, "2025-06-01"),
            ("P00005", 150.0, 600.0, "2025-06-25"),
            ("P00211", 225.0, 900.0, "2025-06-03"),
            ("P00212", 225.0, 900.0, "2025-06-03"),
            ("P00213", 225.0, 900.0, "2025-06-03"),
            ("P00214", 225.0, 900.0, "2025-06-03"),
            ("P00215", 225.0, 900.0, "2025-06-03"),
            ("P00216", 225.0, 900.0, "2025-06-03"),
        ]
        
        for policy_id, amount, ltv, submit_date in policies:
            carrier_data.append({
                "policy_id": policy_id,
                "agent_id": "A001",
                "paid_date": "2025-06-20",
                "amount": amount,
                "status": "active",
                "carrier": "UHC"
            })
            crm_data.append({
                "policy_id": policy_id,
                "agent_id": "A001",
                "submit_date": submit_date,
                "ltv_expected": ltv
            })
        
        carrier = pd.DataFrame(carrier_data)
        crm = pd.DataFrame(crm_data)
        
        result = compute_quotes(carrier, crm)
        assert len(result) == 1
        assert result[0]["agent_id"] == "A001"
        
        # Calculate expected values
        total_earned = sum(amount for _, amount, _, _ in policies)
        total_ltv = sum(ltv for _, _, ltv, _ in policies)
        remaining = total_ltv - total_earned
        expected_advance = remaining * config.ADVANCE_PERCENTAGE
        
        # Should be capped at max advance amount
        assert result[0]["safe_to_advance"] == min(expected_advance, config.MAX_ADVANCE_AMOUNT)
        assert result[0]["safe_to_advance"] == config.MAX_ADVANCE_AMOUNT  # Expecting cap to be hit 