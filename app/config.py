import os
import logging
from typing import Optional


class Config:
    """Application configuration with environment variable support"""
    
    # API Configuration
    API_TITLE: str = "SMS Commission Engine"
    API_VERSION: str = "1.0.0"
    
    # Business Logic Configuration
    ADVANCE_PERCENTAGE: float = float(os.getenv("ADVANCE_PERCENTAGE", "0.80"))
    MAX_ADVANCE_AMOUNT: float = float(os.getenv("MAX_ADVANCE_AMOUNT", "2000.0"))
    ELIGIBILITY_DAYS: int = int(os.getenv("ELIGIBILITY_DAYS", "7"))
    
    # Date Configuration (for testing)
    FROZEN_DATE: Optional[str] = os.getenv("FROZEN_DATE", "2025-07-06")  # YYYY-MM-DD format
    
    # Logging Configuration
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    LOG_FORMAT: str = os.getenv("LOG_FORMAT", "%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    
    # File Upload Configuration
    MAX_FILE_SIZE: int = int(os.getenv("MAX_FILE_SIZE", "10485760"))  # 10MB in bytes
    ALLOWED_EXTENSIONS: set = {".csv"}
    
    # CORS Configuration
    CORS_ORIGINS: list = os.getenv("CORS_ORIGINS", "*").split(",")
    
    @classmethod
    def setup_logging(cls):
        """Configure application logging"""
        logging.basicConfig(
            level=getattr(logging, cls.LOG_LEVEL.upper()),
            format=cls.LOG_FORMAT,
            handlers=[
                logging.StreamHandler(),
            ]
        )
        
        # Set specific logger levels
        logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
        logging.getLogger("uvicorn.error").setLevel(logging.INFO)
        
        logger = logging.getLogger(__name__)
        logger.info(f"Logging configured with level: {cls.LOG_LEVEL}")
        logger.info(f"Configuration loaded: advance_percentage={cls.ADVANCE_PERCENTAGE}, "
                   f"max_advance={cls.MAX_ADVANCE_AMOUNT}, eligibility_days={cls.ELIGIBILITY_DAYS}")


# Global configuration instance
config = Config() 