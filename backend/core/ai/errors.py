"""
Custom exceptions for AI service operations.
Provides unified error handling across all AI modules.
"""
import logging

logger = logging.getLogger(__name__)


class AIServiceError(Exception):
    """Base exception for all AI service errors."""
    
    def __init__(self, message: str, code: str = 'AI_ERROR', details: dict = None):
        self.message = message
        self.code = code
        self.details = details or {}
        super().__init__(self.message)
    
    def to_dict(self):
        """Convert to API response dict."""
        return {
            'error': self.code,
            'message': self.message,
            'details': self.details
        }


class AIAPIError(AIServiceError):
    """Error from OpenAI API call."""
    
    def __init__(self, message: str, status_code: int = None, details: dict = None):
        self.status_code = status_code
        super().__init__(
            message=message,
            code='AI_API_ERROR',
            details={'status_code': status_code, **(details or {})}
        )


class FileProcessingError(AIServiceError):
    """Error during file processing (validation, encoding, etc)."""
    
    def __init__(self, message: str, file_path: str = None, file_type: str = None):
        super().__init__(
            message=message,
            code='FILE_PROCESSING_ERROR',
            details={'file_path': file_path, 'file_type': file_type}
        )


class RateLimitError(AIServiceError):
    """Rate limit exceeded."""
    
    def __init__(self, message: str, retry_after: int = None):
        super().__init__(
            message=message,
            code='RATE_LIMIT_ERROR',
            details={'retry_after_seconds': retry_after}
        )


class TimeoutError(AIServiceError):
    """Operation timeout."""
    
    def __init__(self, message: str, timeout_seconds: float = None):
        super().__init__(
            message=message,
            code='TIMEOUT_ERROR',
            details={'timeout_seconds': timeout_seconds}
        )


class ValidationError(AIServiceError):
    """Data validation error."""
    
    def __init__(self, message: str, field: str = None, expected_type: str = None):
        super().__init__(
            message=message,
            code='VALIDATION_ERROR',
            details={'field': field, 'expected_type': expected_type}
        )
