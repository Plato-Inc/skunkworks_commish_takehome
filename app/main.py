
from fastapi import FastAPI

from app.logging_config import configure_logging
from app.routes.advance import router as advance_router

logger = configure_logging()

app = FastAPI(title="SMS Commission Engine")
app.include_router(advance_router)
