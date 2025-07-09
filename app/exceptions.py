"""Custom exceptions for the commission advance engine"""

class CommissionEngineException(Exception):
    """Base exception for all commission engine errors"""
    pass


class ValidationError(CommissionEngineException):
    """Raised when data validation fails"""
    pass


class BusinessLogicError(CommissionEngineException):
    """Raised when business logic processing fails"""
    pass


class FileProcessingError(CommissionEngineException):
    """Raised when file processing fails"""
    pass


class ConfigurationError(CommissionEngineException):
    """Raised when configuration is invalid"""
    pass