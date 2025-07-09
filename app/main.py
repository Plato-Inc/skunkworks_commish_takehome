from fastapi import FastAPI, UploadFile, File, HTTPException, Request
from fastapi.responses import JSONResponse
import pandas as pd
from io import StringIO
from datetime import datetime
import logging

from .config import config
from .exceptions import ValidationError, BusinessLogicError, FileProcessingError
from .validators import validate_csvs, clean_and_prepare_data
from .business_logic import compute_quotes
from .models import AdvanceQuoteResponse, AgentQuote

# Setup logging
config.setup_logging()
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title=config.API_TITLE,
    version=config.API_VERSION,
    description="Commission advance engine for insurance agents",
)


@app.exception_handler(ValidationError)
async def validation_exception_handler(request: Request, exc: ValidationError):
    """Handle validation errors with clear error messages"""
    logger.error(f"Validation error: {str(exc)}")
    return JSONResponse(
        status_code=400,
        content={
            "error": "Data validation failed",
            "detail": str(exc),
            "type": "validation_error",
        },
    )


@app.exception_handler(BusinessLogicError)
async def business_logic_exception_handler(request: Request, exc: BusinessLogicError):
    """Handle business logic errors"""
    logger.error(f"Business logic error: {str(exc)}")
    return JSONResponse(
        status_code=422,
        content={
            "error": "Business logic processing failed",
            "detail": str(exc),
            "type": "business_logic_error",
        },
    )


@app.exception_handler(FileProcessingError)
async def file_processing_exception_handler(request: Request, exc: FileProcessingError):
    """Handle file processing errors"""
    logger.error(f"File processing error: {str(exc)}")
    return JSONResponse(
        status_code=400,
        content={
            "error": "File processing failed",
            "detail": str(exc),
            "type": "file_processing_error",
        },
    )


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "version": config.API_VERSION,
    }


@app.post("/advance-quote", response_model=AdvanceQuoteResponse)
async def advance_quote(
    carrier_remittance: UploadFile = File(
        ..., description="Carrier remittance CSV file"
    ),
    crm_policies: UploadFile = File(..., description="CRM policies CSV file"),
):
    """
    Calculate commission advance quotes for agents.

    Expects two CSV files:
    - carrier_remittance: Contains payment records with columns: policy_id, agent_id, carrier, paid_date, amount, status
    - crm_policies: Contains policy details with columns: policy_id, agent_id, submit_date, ltv_expected

    Returns per-agent commission advance quotes based on business rules.
    """
    logger.info("Processing advance quote request")

    try:
        # Validate file types
        for file_obj in [carrier_remittance, crm_policies]:
            if not file_obj.filename or not file_obj.filename.endswith(".csv"):
                raise FileProcessingError(
                    f"File {file_obj.filename} must be a CSV file"
                )

            # Check file size
            if file_obj.size and file_obj.size > config.MAX_FILE_SIZE:
                raise FileProcessingError(
                    f"File {file_obj.filename} exceeds maximum size limit"
                )

        # Read CSV files
        try:
            carrier_content = await carrier_remittance.read()
            crm_content = await crm_policies.read()

            carrier_df = pd.read_csv(StringIO(carrier_content.decode("utf-8")))
            crm_df = pd.read_csv(StringIO(crm_content.decode("utf-8")))

            logger.info(
                f"Read {len(carrier_df)} carrier records and {len(crm_df)} CRM records"
            )

        except UnicodeDecodeError as e:
            raise FileProcessingError(f"File encoding error: {str(e)}")
        except pd.errors.EmptyDataError:
            raise FileProcessingError("One or both CSV files are empty")
        except pd.errors.ParserError as e:
            raise FileProcessingError(f"CSV parsing error: {str(e)}")
        except Exception as e:
            raise FileProcessingError(f"Failed to read CSV files: {str(e)}")

        # Validate and clean data
        validate_csvs(carrier_df, crm_df)
        carrier_clean, crm_clean = clean_and_prepare_data(carrier_df, crm_df)

        # Calculate quotes
        try:
            quotes = compute_quotes(carrier_clean, crm_clean)
            # quotes is a list of dicts; convert to AgentQuote dataclasses
            agent_quotes = [AgentQuote(**q) for q in quotes]
            response_obj = AdvanceQuoteResponse(
                generated_at=datetime.utcnow().isoformat(),
                quotes=agent_quotes,
                total_agents=len(agent_quotes),
                total_policies_analyzed=len(crm_clean),
            )
            logger.info(f"Successfully generated quotes for {len(agent_quotes)} agents")
            return response_obj

        except Exception as e:
            raise BusinessLogicError(f"Quote calculation failed: {str(e)}")

    except (ValidationError, BusinessLogicError, FileProcessingError):
        # Re-raise custom exceptions to be handled by exception handlers
        raise
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")
