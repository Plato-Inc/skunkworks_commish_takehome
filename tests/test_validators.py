import pytest
import pandas as pd
from app.validators import (
    validate_carrier_remittance_csv,
    validate_crm_policies_csv,
    validate_csvs,
    clean_and_prepare_data,
    ValidationError,
)


class TestCarrierRemittanceValidation:
    """Test carrier remittance CSV validation"""

    def test_valid_carrier_csv(self):
        """Test valid carrier CSV passes validation"""
        df = pd.DataFrame(
            {
                "policy_id": ["P001", "P002"],
                "agent_id": ["A1", "A2"],
                "carrier": ["Humana", "UHC"],
                "paid_date": ["2025-07-01", "2025-07-02"],
                "amount": [200.0, 150.0],
                "status": ["active", "active"],
            }
        )

        errors = validate_carrier_remittance_csv(df)
        assert len(errors) == 0

    def test_missing_columns(self):
        """Test missing required columns"""
        df = pd.DataFrame(
            {
                "policy_id": ["P001"],
                "agent_id": ["A1"],
                # Missing carrier, paid_date, amount, status
            }
        )

        errors = validate_carrier_remittance_csv(df)
        assert len(errors) == 1
        assert "Missing required columns" in errors[0]

    def test_empty_policy_id(self):
        """Test empty policy_id"""
        df = pd.DataFrame(
            {
                "policy_id": ["", "P002"],
                "agent_id": ["A1", "A2"],
                "carrier": ["Humana", "UHC"],
                "paid_date": ["2025-07-01", "2025-07-02"],
                "amount": [200.0, 150.0],
                "status": ["active", "active"],
            }
        )

        errors = validate_carrier_remittance_csv(df)
        assert len(errors) == 1
        assert "policy_id cannot be empty" in errors[0]

    def test_invalid_date_format(self):
        """Test invalid date format"""
        df = pd.DataFrame(
            {
                "policy_id": ["P001"],
                "agent_id": ["A1"],
                "carrier": ["Humana"],
                "paid_date": ["2025/07/01"],  # Wrong format
                "amount": [200.0],
                "status": ["active"],
            }
        )

        errors = validate_carrier_remittance_csv(df)
        assert len(errors) == 1
        assert "paid_date must be in YYYY-MM-DD format" in errors[0]

    def test_invalid_amount(self):
        """Test invalid amount"""
        df = pd.DataFrame(
            {
                "policy_id": ["P001"],
                "agent_id": ["A1"],
                "carrier": ["Humana"],
                "paid_date": ["2025-07-01"],
                "amount": ["invalid"],
                "status": ["active"],
            }
        )

        errors = validate_carrier_remittance_csv(df)
        assert len(errors) == 1
        assert "amount must be a valid number" in errors[0]

    def test_negative_amount_allowed(self):
        """Test that negative amounts are allowed (for claw-backs)"""
        df = pd.DataFrame(
            {
                "policy_id": ["P001"],
                "agent_id": ["A1"],
                "carrier": ["Humana"],
                "paid_date": ["2025-07-01"],
                "amount": [-200.0],  # Negative amount for claw-back
                "status": ["cancelled"],
            }
        )

        errors = validate_carrier_remittance_csv(df)
        assert len(errors) == 0

    def test_invalid_status(self):
        """Test invalid status"""
        df = pd.DataFrame(
            {
                "policy_id": ["P001"],
                "agent_id": ["A1"],
                "carrier": ["Humana"],
                "paid_date": ["2025-07-01"],
                "amount": [200.0],
                "status": ["invalid_status"],
            }
        )

        errors = validate_carrier_remittance_csv(df)
        assert len(errors) == 1
        assert "status must be one of" in errors[0]


class TestCRMPoliciesValidation:
    """Test CRM policies CSV validation"""

    def test_valid_crm_csv(self):
        """Test valid CRM CSV passes validation"""
        df = pd.DataFrame(
            {
                "policy_id": ["P001", "P002"],
                "agent_id": ["A1", "A2"],
                "submit_date": ["2025-06-01", "2025-06-02"],
                "ltv_expected": [800.0, 900.0],
            }
        )

        errors = validate_crm_policies_csv(df)
        assert len(errors) == 0

    def test_missing_columns(self):
        """Test missing required columns"""
        df = pd.DataFrame(
            {
                "policy_id": ["P001"],
                "agent_id": ["A1"],
                # Missing submit_date, ltv_expected
            }
        )

        errors = validate_crm_policies_csv(df)
        assert len(errors) == 1
        assert "Missing required columns" in errors[0]

    def test_negative_ltv(self):
        """Test negative LTV expected"""
        df = pd.DataFrame(
            {
                "policy_id": ["P001"],
                "agent_id": ["A1"],
                "submit_date": ["2025-06-01"],
                "ltv_expected": [-800.0],  # Negative LTV
            }
        )

        errors = validate_crm_policies_csv(df)
        assert len(errors) == 1
        assert "ltv_expected must be non-negative" in errors[0]

    def test_invalid_ltv(self):
        """Test invalid LTV value"""
        df = pd.DataFrame(
            {
                "policy_id": ["P001"],
                "agent_id": ["A1"],
                "submit_date": ["2025-06-01"],
                "ltv_expected": ["invalid"],
            }
        )

        errors = validate_crm_policies_csv(df)
        assert len(errors) == 1
        assert "ltv_expected must be a valid positive number" in errors[0]


class TestValidateCSVs:
    """Test combined CSV validation"""

    def test_valid_csvs(self):
        """Test that valid CSVs pass validation"""
        carrier_df = pd.DataFrame(
            {
                "policy_id": ["P001"],
                "agent_id": ["A1"],
                "carrier": ["Humana"],
                "paid_date": ["2025-07-01"],
                "amount": [200.0],
                "status": ["active"],
            }
        )
        crm_df = pd.DataFrame(
            {
                "policy_id": ["P001"],
                "agent_id": ["A1"],
                "submit_date": ["2025-06-01"],
                "ltv_expected": [800.0],
            }
        )

        # Should not raise exception
        validate_csvs(carrier_df, crm_df)

    def test_invalid_csvs_raise_exception(self):
        """Test that invalid CSVs raise ValidationError"""
        carrier_df = pd.DataFrame(
            {
                "policy_id": [""],  # Empty policy_id
                "agent_id": ["A1"],
                "carrier": ["Humana"],
                "paid_date": ["2025-07-01"],
                "amount": [200.0],
                "status": ["active"],
            }
        )
        crm_df = pd.DataFrame(
            {
                "policy_id": ["P001"],
                "agent_id": ["A1"],
                "submit_date": ["2025-06-01"],
                "ltv_expected": [-800.0],  # Negative LTV
            }
        )

        with pytest.raises(ValidationError) as exc_info:
            validate_csvs(carrier_df, crm_df)

        error_message = str(exc_info.value)
        assert "CSV validation failed" in error_message
        assert "policy_id cannot be empty" in error_message
        assert "ltv_expected must be non-negative" in error_message


class TestCleanAndPrepareData:
    """Test data cleaning and preparation"""

    def test_data_cleaning(self):
        """Test that data is properly cleaned and prepared"""
        carrier_df = pd.DataFrame(
            {
                "policy_id": [" P001 ", "P002"],
                "agent_id": [" A1 ", "A2"],
                "carrier": ["Humana", "UHC"],
                "paid_date": ["2025-07-01", "2025-07-02"],
                "amount": ["200.0", "150.0"],  # String amounts
                "status": [" ACTIVE ", "Active"],  # Mixed case
            }
        )
        crm_df = pd.DataFrame(
            {
                "policy_id": [" P001 ", "P002"],
                "agent_id": [" A1 ", "A2"],
                "submit_date": ["2025-06-01", "2025-06-02"],
                "ltv_expected": ["800.0", "900.0"],  # String LTV
            }
        )

        carrier_clean, crm_clean = clean_and_prepare_data(carrier_df, crm_df)

        # Check that strings are trimmed
        assert carrier_clean.iloc[0]["policy_id"] == "P001"
        assert carrier_clean.iloc[0]["agent_id"] == "A1"

        # Check that amounts are converted to float
        assert isinstance(carrier_clean.iloc[0]["amount"], (int, float))
        assert carrier_clean.iloc[0]["amount"] == 200.0

        # Check that status is lowercase
        assert carrier_clean.iloc[0]["status"] == "active"

        # Check that dates are converted to date objects
        from datetime import date

        assert isinstance(carrier_clean.iloc[0]["paid_date"], date)
        assert isinstance(crm_clean.iloc[0]["submit_date"], date)

        # Check that LTV is converted to float
        assert isinstance(crm_clean.iloc[0]["ltv_expected"], (int, float))
        assert crm_clean.iloc[0]["ltv_expected"] == 800.0


class TestEmptyDataValidation:
    """Test validation with empty data"""

    def test_empty_carrier_csv(self):
        """Test empty carrier CSV"""
        df = pd.DataFrame(
            {
                "policy_id": [],
                "agent_id": [],
                "carrier": [],
                "paid_date": [],
                "amount": [],
                "status": [],
            }
        )

        errors = validate_carrier_remittance_csv(df)
        assert len(errors) == 1
        assert "Carrier remittance CSV is empty" in errors[0]

    def test_empty_crm_csv(self):
        """Test empty CRM CSV"""
        df = pd.DataFrame(
            {"policy_id": [], "agent_id": [], "submit_date": [], "ltv_expected": []}
        )

        errors = validate_crm_policies_csv(df)
        assert len(errors) == 1
        assert "CRM policies CSV is empty" in errors[0]
