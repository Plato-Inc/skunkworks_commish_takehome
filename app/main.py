
from fastapi import FastAPI

from app.routes.v1.advance import router as advance_router

app = FastAPI(title="SMS Commission Engine")
app.include_router(advance_router)
