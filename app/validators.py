import pandas as pd
from datetime import datetime
from typing import List, Tuple
import logging

from .exceptions import ValidationError

logger = logging.getLogger(__name__)


def validate_carrier_remittance_csv(df: pd.DataFrame) -> List[str]:
    """
    Validate carrier remittance CSV structure and data quality.

    Returns:
        List of validation error messages (empty if valid)
    """
    errors = []

    # Check required columns
    required_columns = {
        "policy_id",
        "agent_id",
        "carrier",
        "paid_date",
        "amount",
        "status",
    }
    missing_columns = required_columns - set(df.columns)
    if missing_columns:
        errors.append(
            f"Missing required columns in carrier remittance: {missing_columns}"
        )
        return errors  # Can't continue without required columns

    # Check for empty DataFrame
    if df.empty:
        errors.append("Carrier remittance CSV is empty")
        return errors

    # Validate data types and values
    for row_idx in range(len(df)):
        row_errors = []
        actual_row_num = row_idx + 2  # Add 2 for header and 0-based index

        # Validate policy_id
        policy_id_val = df.iloc[row_idx]["policy_id"]
        if pd.isna(policy_id_val) or str(policy_id_val).strip() == "":
            row_errors.append("policy_id cannot be empty")

        # Validate agent_id
        agent_id_val = df.iloc[row_idx]["agent_id"]
        if pd.isna(agent_id_val) or str(agent_id_val).strip() == "":
            row_errors.append("agent_id cannot be empty")

        # Validate paid_date
        try:
            paid_date_val = df.iloc[row_idx]["paid_date"]
            if pd.isna(paid_date_val):
                row_errors.append("paid_date cannot be empty")
            else:
                datetime.strptime(str(paid_date_val), "%Y-%m-%d")
        except ValueError:
            row_errors.append(
                f"paid_date must be in YYYY-MM-DD format, got: {df.iloc[row_idx]['paid_date']}"
            )

        # Validate amount
        try:
            amount = float(df.iloc[row_idx]["amount"])
            # Allow negative amounts for claw-backs
        except (ValueError, TypeError):
            row_errors.append(
                f"amount must be a valid number, got: {df.iloc[row_idx]['amount']}"
            )

        # Validate status
        valid_statuses = {"active", "cancelled"}
        status_val = df.iloc[row_idx]["status"]
        if pd.isna(status_val) or str(status_val).lower() not in valid_statuses:
            row_errors.append(
                f"status must be one of {valid_statuses}, got: {df.iloc[row_idx]['status']}"
            )

        if row_errors:
            errors.append(f"Row {actual_row_num}: {'; '.join(row_errors)}")

    return errors


def validate_crm_policies_csv(df: pd.DataFrame) -> List[str]:
    """
    Validate CRM policies CSV structure and data quality.

    Returns:
        List of validation error messages (empty if valid)
    """
    errors = []

    # Check required columns
    required_columns = {"policy_id", "agent_id", "submit_date", "ltv_expected"}
    missing_columns = required_columns - set(df.columns)
    if missing_columns:
        errors.append(f"Missing required columns in CRM policies: {missing_columns}")
        return errors  # Can't continue without required columns

    # Check for empty DataFrame
    if df.empty:
        errors.append("CRM policies CSV is empty")
        return errors

    # Validate data types and values
    for row_idx in range(len(df)):
        row_errors = []
        actual_row_num = row_idx + 2  # Add 2 for header and 0-based index

        # Validate policy_id
        policy_id_val = df.iloc[row_idx]["policy_id"]
        if pd.isna(policy_id_val) or str(policy_id_val).strip() == "":
            row_errors.append("policy_id cannot be empty")

        # Validate agent_id
        agent_id_val = df.iloc[row_idx]["agent_id"]
        if pd.isna(agent_id_val) or str(agent_id_val).strip() == "":
            row_errors.append("agent_id cannot be empty")

        # Validate submit_date
        try:
            submit_date_val = df.iloc[row_idx]["submit_date"]
            if pd.isna(submit_date_val):
                row_errors.append("submit_date cannot be empty")
            else:
                datetime.strptime(str(submit_date_val), "%Y-%m-%d")
        except ValueError:
            row_errors.append(
                f"submit_date must be in YYYY-MM-DD format, got: {df.iloc[row_idx]['submit_date']}"
            )

        # Validate ltv_expected
        try:
            ltv = float(df.iloc[row_idx]["ltv_expected"])
            if ltv < 0:
                row_errors.append(f"ltv_expected must be non-negative, got: {ltv}")
        except (ValueError, TypeError):
            row_errors.append(
                f"ltv_expected must be a valid positive number, got: {df.iloc[row_idx]['ltv_expected']}"
            )

        if row_errors:
            errors.append(f"Row {actual_row_num}: {'; '.join(row_errors)}")

    return errors


def validate_csvs(carrier_df: pd.DataFrame, crm_df: pd.DataFrame) -> None:
    """
    Validate both CSV inputs and raise ValidationError if any issues found.

    Args:
        carrier_df: Carrier remittance DataFrame
        crm_df: CRM policies DataFrame

    Raises:
        ValidationError: If validation fails
    """
    all_errors = []

    # Validate carrier remittance
    carrier_errors = validate_carrier_remittance_csv(carrier_df)
    if carrier_errors:
        all_errors.extend([f"Carrier Remittance - {error}" for error in carrier_errors])

    # Validate CRM policies
    crm_errors = validate_crm_policies_csv(crm_df)
    if crm_errors:
        all_errors.extend([f"CRM Policies - {error}" for error in crm_errors])

    if all_errors:
        error_message = "CSV validation failed:\n" + "\n".join(all_errors)
        logger.error(f"Data validation failed: {error_message}")
        raise ValidationError(error_message)

    logger.info("CSV validation passed successfully")


def clean_and_prepare_data(
    carrier_df: pd.DataFrame, crm_df: pd.DataFrame
) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """
    Clean and prepare data for processing after validation.

    Args:
        carrier_df: Raw carrier remittance DataFrame
        crm_df: Raw CRM policies DataFrame

    Returns:
        Tuple of cleaned DataFrames
    """
    # Clean carrier data
    carrier_clean = carrier_df.copy()
    carrier_clean["paid_date"] = pd.to_datetime(carrier_clean["paid_date"]).dt.date
    carrier_clean["amount"] = pd.to_numeric(carrier_clean["amount"])
    carrier_clean["status"] = carrier_clean["status"].str.lower().str.strip()
    carrier_clean["policy_id"] = carrier_clean["policy_id"].str.strip()
    carrier_clean["agent_id"] = carrier_clean["agent_id"].str.strip()

    # Clean CRM data
    crm_clean = crm_df.copy()
    crm_clean["submit_date"] = pd.to_datetime(crm_clean["submit_date"]).dt.date
    crm_clean["ltv_expected"] = pd.to_numeric(crm_clean["ltv_expected"])
    crm_clean["policy_id"] = crm_clean["policy_id"].str.strip()
    crm_clean["agent_id"] = crm_clean["agent_id"].str.strip()

    logger.info(
        f"Cleaned data: {len(carrier_clean)} carrier records, {len(crm_clean)} CRM records"
    )

    return carrier_clean, crm_clean
