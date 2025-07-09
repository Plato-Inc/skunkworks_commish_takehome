from datetime import datetime, timezone

from fastapi import APIRouter, File, HTTPException, UploadFile, status

from app.logging_config import configure_logging
from app.quotes import compute_quotes
from app.utils import _read_csv_file, _validate_csv_files

logger = configure_logging()

router = APIRouter(prefix="/v1")


@router.post("/advance-quote")
async def advance_quote(
    carrier_remittance: UploadFile = File(..., description="Carrier remittance CSV file"),
    crm_policies: UploadFile = File(..., description="CRM policies CSV file"),
):
    logger.info(f"Processing advance quote request with files: {carrier_remittance.filename}, {crm_policies.filename}")
    # Validate file types
    if not _validate_csv_files(carrier_remittance, crm_policies):
        logger.warning(f"Invalid file types submitted: {carrier_remittance.filename}, {crm_policies.filename}")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Both uploads must be valid CSV files with .csv extension")
    try:
        # Read CSV files with error handling
        carrier_df = _read_csv_file(carrier_remittance, "carrier_remittance")
        crm_df = _read_csv_file(crm_policies, "crm_policies")
        logger.info(f"Successfully read CSV files. Carrier records: {len(carrier_df)}, CRM records: {len(crm_df)}")
        quotes = compute_quotes(carrier_df, crm_df)
        logger.info(f"Successfully generated quotes for {len(quotes)} agents")
        return {"generated_at": datetime.now(timezone.utc).isoformat(), "quotes": quotes}
    except ValueError as e:
        logger.error(f"CSV validation error: {str(e)}")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Invalid CSV format: {str(e)}")
    except Exception:
        logger.error("Unexpected error during quote generation", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error")
