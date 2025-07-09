import pytest
import pandas as pd
from pathlib import Path
from datetime import timedelta

from app.business_logic import (
    compute_quotes,
    get_detailed_agent_quotes,
    analyze_policies,
    calculate_agent_quotes,
    get_today
)
from app.config import config


class TestSampleDataIntegration:
    """Integration tests using the actual sample data files"""

    @pytest.fixture(scope="class")
    def sample_data_path(self):
        """Get path to sample data directory"""
        return Path(__file__).parent.parent / "sample_data"

    @pytest.fixture(scope="class")
    def carrier_data(self, sample_data_path):
        """Load actual carrier remittance data"""
        return pd.read_csv(sample_data_path / "carrier_remittance.csv")

    @pytest.fixture(scope="class")
    def crm_data(self, sample_data_path):
        """Load actual CRM policies data"""
        return pd.read_csv(sample_data_path / "crm_policies.csv")

    def test_agent_a001_cap_with_real_data(self, carrier_data, crm_data):
        """Test that agent A001 hits the $2,000 cap using actual sample data"""
        # Run the business logic with real data
        result = compute_quotes(carrier_data, crm_data)

        # Find A001 in the results
        a001_quote = None
        for quote in result:
            if quote["agent_id"] == "A001":
                a001_quote = quote
                break

        assert a001_quote is not None, "Agent A001 should be found in results"

        # Verify A001 hits the $2,000 cap
        assert a001_quote["safe_to_advance"] == 2000.0, f"A001 should hit $2,000 cap, got {a001_quote['safe_to_advance']}"

        # Verify the earned amount is reasonable
        assert a001_quote["earned_to_date"] > 0, "A001 should have earned some amount"

        # Verify the eligible remaining is substantial enough to hit the cap
        assert a001_quote["total_eligible_remaining"] > 0, "A001 should have eligible remaining amount"

        # Verify that 80% of eligible remaining exceeds the cap
        expected_advance_without_cap = a001_quote["total_eligible_remaining"] * config.ADVANCE_PERCENTAGE
        assert expected_advance_without_cap > config.MAX_ADVANCE_AMOUNT, \
            f"A001's calculated advance ({expected_advance_without_cap}) should exceed cap ({config.MAX_ADVANCE_AMOUNT})"

        # Verify policy count
        assert a001_quote["eligible_policies_count"] > 0, "A001 should have eligible policies"

        print(f"✓ A001 Results:")
        print(f"  Earned to date: ${a001_quote['earned_to_date']:,.2f}")
        print(f"  Total eligible remaining: ${a001_quote['total_eligible_remaining']:,.2f}")
        print(f"  80% of eligible remaining: ${expected_advance_without_cap:,.2f}")
        print(f"  Safe to advance (capped): ${a001_quote['safe_to_advance']:,.2f}")
        print(f"  Eligible policies count: {a001_quote['eligible_policies_count']}")

    def test_a001_detailed_policy_analysis(self, carrier_data, crm_data):
        """Test detailed analysis of A001's policies to verify eligibility logic"""
        # Get detailed quotes to access the policy analysis
        detailed_quotes = get_detailed_agent_quotes(carrier_data, crm_data)

        # Find A001
        a001_quote = None
        for quote in detailed_quotes:
            if quote.agent_id == "A001":
                a001_quote = quote
                break

        assert a001_quote is not None, "Agent A001 should be found in detailed results"

        # Analyze policies for A001 to understand eligibility
        policy_analyses = analyze_policies(carrier_data, crm_data)
        a001_policies = [p for p in policy_analyses if p.agent_id == "A001"]

        # Count eligible vs ineligible policies
        eligible_policies = [p for p in a001_policies if p.is_eligible]
        ineligible_policies = [p for p in a001_policies if not p.is_eligible]

        # Calculate expected values
        total_eligible_remaining = sum(p.remaining_expected for p in eligible_policies)
        total_earned = sum(p.earned_to_date for p in a001_policies)

        # Verify calculations match the quote
        assert abs(a001_quote.total_eligible_remaining - total_eligible_remaining) < 0.01, \
            f"Eligible remaining mismatch: {a001_quote.total_eligible_remaining} vs {total_eligible_remaining}"

        assert abs(a001_quote.earned_to_date - total_earned) < 0.01, \
            f"Earned to date mismatch: {a001_quote.earned_to_date} vs {total_earned}"

        # Verify eligibility logic
        today = get_today()
        cutoff_date = today - timedelta(days=config.ELIGIBILITY_DAYS)

        for policy in eligible_policies:
            assert policy.latest_status == "active", f"Eligible policy {policy.policy_id} should be active"
            assert policy.submit_date <= cutoff_date, f"Eligible policy {policy.policy_id} should be submitted by {cutoff_date}"

        for policy in ineligible_policies:
            assert policy.latest_status != "active" or policy.submit_date > cutoff_date, \
                f"Ineligible policy {policy.policy_id} should either be inactive or submitted after {cutoff_date}"

        print(f"✓ A001 Policy Analysis:")
        print(f"  Total policies: {len(a001_policies)}")
        print(f"  Eligible policies: {len(eligible_policies)}")
        print(f"  Ineligible policies: {len(ineligible_policies)}")
        print(f"  Eligibility cutoff date: {cutoff_date}")
        print(f"  Total eligible remaining: ${total_eligible_remaining:,.2f}")
        print(f"  Total earned: ${total_earned:,.2f}")

    def test_cap_logic_with_multiple_agents(self, carrier_data, crm_data):
        """Test that the cap logic works correctly across multiple agents"""
        result = compute_quotes(carrier_data, crm_data)

        # Count how many agents hit the cap
        agents_hitting_cap = 0
        agents_not_hitting_cap = 0

        for quote in result:
            eligible_remaining = quote["total_eligible_remaining"]
            calculated_advance = eligible_remaining * config.ADVANCE_PERCENTAGE

            if calculated_advance > config.MAX_ADVANCE_AMOUNT:
                # Should be capped
                assert quote["safe_to_advance"] == config.MAX_ADVANCE_AMOUNT, \
                    f"Agent {quote['agent_id']} should hit cap but got {quote['safe_to_advance']}"
                agents_hitting_cap += 1
            else:
                # Should not be capped
                assert abs(quote["safe_to_advance"] - calculated_advance) < 0.01, \
                    f"Agent {quote['agent_id']} should not hit cap but got {quote['safe_to_advance']} vs {calculated_advance}"
                agents_not_hitting_cap += 1

        print(f"✓ Cap Analysis:")
        print(f"  Agents hitting cap: {agents_hitting_cap}")
        print(f"  Agents not hitting cap: {agents_not_hitting_cap}")
        print(f"  Total agents: {len(result)}")

        # Verify A001 specifically hits the cap
        a001_quote = next(q for q in result if q["agent_id"] == "A001")
        assert a001_quote["safe_to_advance"] == config.MAX_ADVANCE_AMOUNT, \
            f"A001 should hit the cap as per FAQ #10"

    def test_business_rules_compliance(self, carrier_data, crm_data):
        """Test that the business rules from the README are correctly implemented"""
        result = compute_quotes(carrier_data, crm_data)

        # Verify the rules for each agent
        for quote in result:
            # Rule 1: Earned to date should be sum of payments
            # Rule 2: Remaining expected = ltv_expected - earned_to_date (but not negative)
            # Rule 3: Policy eligible when status=active AND submit_date <= today - 7 days
            # Rule 4: Safe-to-advance = min(0.80 × Σ remaining_expected (eligible), $2,000)

            agent_id = quote["agent_id"]

            # Basic sanity checks
            assert quote["earned_to_date"] >= 0, f"Earned amount should be non-negative for {agent_id}"
            assert quote["total_eligible_remaining"] >= 0, f"Eligible remaining should be non-negative for {agent_id}"
            assert quote["safe_to_advance"] >= 0, f"Safe to advance should be non-negative for {agent_id}"
            assert quote["safe_to_advance"] <= config.MAX_ADVANCE_AMOUNT, f"Safe to advance should not exceed cap for {agent_id}"
            assert quote["eligible_policies_count"] >= 0, f"Eligible policies count should be non-negative for {agent_id}"

            # Rule 4 verification
            calculated_advance = quote["total_eligible_remaining"] * config.ADVANCE_PERCENTAGE
            expected_safe_amount = min(calculated_advance, config.MAX_ADVANCE_AMOUNT)
            assert abs(quote["safe_to_advance"] - expected_safe_amount) < 0.01, \
                f"Safe to advance calculation incorrect for {agent_id}: {quote['safe_to_advance']} vs {expected_safe_amount}"

        print(f"✓ Business Rules Compliance verified for {len(result)} agents")

    def test_sample_data_integrity(self, carrier_data, crm_data):
        """Test that the sample data files are properly structured"""
        # Check carrier data structure
        required_carrier_columns = ["policy_id", "agent_id", "paid_date", "amount", "status"]
        for col in required_carrier_columns:
            assert col in carrier_data.columns, f"Missing column {col} in carrier data"

        # Check CRM data structure
        required_crm_columns = ["policy_id", "agent_id", "submit_date", "ltv_expected"]
        for col in required_crm_columns:
            assert col in crm_data.columns, f"Missing column {col} in CRM data"

        # Check data types and values
        assert carrier_data["amount"].dtype in ["float64", "int64"], "Amount should be numeric"
        assert crm_data["ltv_expected"].dtype in ["float64", "int64"], "LTV expected should be numeric"

        # Check that A001 exists in both datasets
        assert "A001" in carrier_data["agent_id"].values, "A001 should exist in carrier data"
        assert "A001" in crm_data["agent_id"].values, "A001 should exist in CRM data"

        # Check that A001 has policies
        a001_carrier_policies = carrier_data[carrier_data["agent_id"] == "A001"]["policy_id"].nunique()
        a001_crm_policies = crm_data[crm_data["agent_id"] == "A001"]["policy_id"].nunique()

        assert a001_carrier_policies > 0, "A001 should have policies in carrier data"
        assert a001_crm_policies > 0, "A001 should have policies in CRM data"

        print(f"✓ Sample Data Integrity:")
        print(f"  Carrier records: {len(carrier_data)}")
        print(f"  CRM records: {len(crm_data)}")
        print(f"  A001 carrier policies: {a001_carrier_policies}")
        print(f"  A001 CRM policies: {a001_crm_policies}")
        print(f"  Total agents in carrier: {carrier_data['agent_id'].nunique()}")
        print(f"  Total agents in CRM: {crm_data['agent_id'].nunique()}")