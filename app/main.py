import logging
from datetime import datetime, timedelta, timezone
from io import StringIO

import pandas as pd
from fastapi import FastAPI, File, HTTPException, UploadFile

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="SMS Commission Engine")

TODAY = datetime(2025, 7, 6).date()  # freeze for reproducibility; replace with datetime.utcnow().date()

def safe_float(x):
    try:
        return float(x)
    except Exception:
        return 0.0

def _validate_csv_files(*files: UploadFile) -> bool:
    """Validate that all uploaded files are CSV files."""
    for file in files:
        if not file.filename or not file.filename.lower().endswith('.csv'):
            return False
    return True

def _read_csv_file(file: UploadFile, file_name: str) -> pd.DataFrame:
    """Read and validate CSV file content."""
    try:
        content = file.file.read()
        file.file.seek(0)  # Reset file pointer for potential reuse
        return pd.read_csv(StringIO(content.decode('utf-8')))
    except UnicodeDecodeError:
        raise ValueError(f"{file_name} contains invalid UTF-8 encoding")
    except pd.errors.EmptyDataError:
        raise ValueError(f"{file_name} is empty")
    except pd.errors.ParserError:
        raise ValueError(f"{file_name} has invalid CSV format")

def compute_quotes(carrier_df: pd.DataFrame, crm_df: pd.DataFrame):
    # Merge on policy_id & agent_id for safety
    merged = pd.merge(carrier_df, crm_df, on=["policy_id", "agent_id"], suffixes=("_carrier", "_crm"))
    # Earned to date
    earned = merged.groupby(["policy_id", "agent_id"])["amount"].sum().reset_index()
    earned = earned.rename(columns={"amount": "earned_to_date"})
    merged = pd.merge(merged.drop(columns="amount"), earned, on=["policy_id", "agent_id"])
    merged["remaining_expected"] = merged["ltv_expected"] - merged["earned_to_date"]
    # Advance‑eligibility
    merged["submit_date"] = pd.to_datetime(merged["submit_date"]).dt.date
    merged["eligible"] = (merged["status"] == "active") & (merged["submit_date"] <= TODAY - timedelta(days=7))
    eligible = merged[merged["eligible"]]
    advance = eligible.groupby("agent_id")["remaining_expected"].sum().reset_index()
    advance["safe_to_advance"] = advance["remaining_expected"] * 0.8
    advance["safe_to_advance"] = advance["safe_to_advance"].clip(upper=2000)
    # Earned per agent
    earned_total = merged.groupby("agent_id")["earned_to_date"].sum().reset_index()
    result = pd.merge(earned_total, advance.drop(columns="remaining_expected"), on="agent_id", how="left").fillna(0)
    return result.to_dict(orient="records")

@app.post("/advance-quote")
async def advance_quote(
    carrier_remittance: UploadFile = File(..., description="Carrier remittance CSV file"),
    crm_policies: UploadFile = File(..., description="CRM policies CSV file")
):
    logger.info(f"Processing advance quote request with files: {carrier_remittance.filename}, {crm_policies.filename}")
    
    # Validate file types
    if not _validate_csv_files(carrier_remittance, crm_policies):
        logger.warning(f"Invalid file types submitted: {carrier_remittance.filename}, {crm_policies.filename}")
        raise HTTPException(
            status_code=400, 
            detail="Both uploads must be valid CSV files with .csv extension"
        )
    
    try:
        # Read CSV files with error handling
        carrier_df = _read_csv_file(carrier_remittance, "carrier_remittance")
        crm_df = _read_csv_file(crm_policies, "crm_policies")
        
        logger.info(f"Successfully read CSV files. Carrier records: {len(carrier_df)}, CRM records: {len(crm_df)}")
        
        quotes = compute_quotes(carrier_df, crm_df)
        
        logger.info(f"Successfully generated quotes for {len(quotes)} agents")
        
        return {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "quotes": quotes
        }
    except ValueError as e:
        logger.error(f"CSV validation error: {str(e)}")
        raise HTTPException(status_code=400, detail=f"Invalid CSV format: {str(e)}")
    except Exception:
        logger.error("Unexpected error during quote generation", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")
