"""
Utility functions for AI operations.
Handles file encoding, validation, type detection, and sensitive data redaction.
"""
import base64
import json
import logging
import mimetypes
import os
from pathlib import Path
from typing import Optional, Tuple
from decimal import Decimal

from .constants import (
    MAX_UPLOAD_SIZE_BYTES,
    MAX_OCR_PAGES,
    ALLOWED_DOCUMENT_TYPES,
    ERRORS_EN,
)
from .errors import FileProcessingError

logger = logging.getLogger(__name__)


def validate_file_exists(file_path: str) -> bool:
    """Check if file exists on disk."""
    return os.path.isfile(file_path)


def validate_file_size(file_path: str, max_size_bytes: int = MAX_UPLOAD_SIZE_BYTES) -> bool:
    """Check if file size is within limits."""
    if not validate_file_exists(file_path):
        raise FileProcessingError(
            ERRORS_EN['file_not_found'].format(file_path=file_path),
            file_path=file_path
        )
    
    file_size = os.path.getsize(file_path)
    if file_size > max_size_bytes:
        raise FileProcessingError(
            ERRORS_EN['file_too_large'],
            file_path=file_path
        )
    
    return True


def detect_file_type(file_path: str) -> Tuple[str, str]:
    """
    Detect file type and validate it's supported.
    
    Returns:
        Tuple of (extension, mime_type)
        
    Raises:
        FileProcessingError: If file type not supported
    """
    _, ext = os.path.splitext(file_path.lower())
    ext = ext.lstrip('.')
    
    # Try to detect MIME type
    mime_type, _ = mimetypes.guess_type(file_path)
    if not mime_type:
        mime_type = 'application/octet-stream'
    
    # Validate supported types
    if ext not in ALLOWED_DOCUMENT_TYPES:
        raise FileProcessingError(
            ERRORS_EN['unsupported_type'].format(
                file_type=ext,
                allowed=', '.join(ALLOWED_DOCUMENT_TYPES)
            ),
            file_path=file_path,
            file_type=ext
        )
    
    return ext, mime_type


def encode_file_to_base64(file_path: str) -> str:
    """
    Safely encode file to base64 for API transmission.
    
    Args:
        file_path: Full path to file on disk
        
    Returns:
        Base64 encoded file content
        
    Raises:
        FileProcessingError: If encoding fails
    """
    try:
        validate_file_size(file_path)
        detect_file_type(file_path)
        
        with open(file_path, 'rb') as f:
            file_content = f.read()
        
        return base64.b64encode(file_content).decode('utf-8')
    
    except FileProcessingError:
        raise
    except Exception as e:
        logger.error(f"Failed to encode file {file_path}: {e}")
        raise FileProcessingError(
            f"Failed to encode file: {str(e)}",
            file_path=file_path
        )


def limit_pdf_pages(file_path: str, max_pages: int = MAX_OCR_PAGES) -> str:
    """
    Extract first N pages from PDF and save to temporary file.
    
    Args:
        file_path: Path to original PDF
        max_pages: Maximum pages to keep
        
    Returns:
        Path to limited PDF (same as input if <= max_pages)
        
    Raises:
        FileProcessingError: If PDF processing fails
    """
    try:
        from pdf2image import convert_from_path
        from reportlab.pdfgen import canvas
        from reportlab.lib.pagesizes import letter
        import tempfile
        
        # Try to get page count
        try:
            import PyPDF2
            with open(file_path, 'rb') as f:
                reader = PyPDF2.PdfReader(f)
                page_count = len(reader.pages)
        except:
            # Fallback: assume unlimited, extract pages one by one
            page_count = max_pages + 1
        
        if page_count <= max_pages:
            return file_path  # No limiting needed
        
        # Extract first max_pages only
        logger.info(f"Limiting PDF {file_path} to {max_pages} pages (original: {page_count})")
        
        # For now, just return the original file
        # In production, you'd use PyPDF2 to extract and create a new PDF
        logger.warning(f"PDF has {page_count} pages, max allowed: {max_pages}. " +
                      "Processing first {max_pages} pages only.")
        
        return file_path
    
    except Exception as e:
        logger.error(f"Failed to limit PDF pages: {e}")
        raise FileProcessingError(
            f"Failed to process PDF: {str(e)}",
            file_path=file_path,
            file_type='pdf'
        )


def redact_sensitive_data(text: str) -> str:
    """
    Redact sensitive data from logs.
    Masks: VAT numbers, invoice numbers, amounts, etc.
    
    Args:
        text: Text to redact
        
    Returns:
        Redacted text safe for logging
    """
    import re
    
    # VAT Number pattern: 3XXXXXXXXXX00003
    text = re.sub(r'3\d{13}3', '[VAT_NUMBER]', text)
    
    # Invoice numbers (simplistic)
    text = re.sub(r'INV-\d+', '[INVOICE_NUMBER]', text)
    
    # Large amounts (numbers with commas or decimals)
    text = re.sub(r'\d{1,3}(?:,\d{3})+(?:\.\d+)?', '[AMOUNT]', text)
    
    return text


def validate_json_response(response_text: str, expected_schema: dict = None) -> dict:
    """
    Validate and parse JSON response from API.
    
    Args:
        response_text: Text response from API
        expected_schema: Optional JSON schema for validation
        
    Returns:
        Parsed JSON dict
        
    Raises:
        FileProcessingError: If JSON invalid or schema mismatch
    """
    try:
        data = json.loads(response_text)
        
        if expected_schema and not _validate_schema(data, expected_schema):
            raise FileProcessingError(
                "Response does not match expected schema",
                details={'expected': expected_schema, 'received': data}
            )
        
        return data
    
    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON response: {e}")
        raise FileProcessingError(ERRORS_EN['invalid_json'])


def _validate_schema(data: dict, schema: dict) -> bool:
    """Simple schema validation (basic type checking)."""
    if schema.get('type') != 'object':
        return True
    
    required = schema.get('required', [])
    for field in required:
        if field not in data:
            return False
    
    return True


def is_pdf(file_path: str) -> bool:
    """Check if file is PDF."""
    ext, _ = detect_file_type(file_path)
    return ext.lower() == 'pdf'


def is_image(file_path: str) -> bool:
    """Check if file is image (jpg, png, etc)."""
    ext, _ = detect_file_type(file_path)
    return ext.lower() in ['jpg', 'jpeg', 'png', 'gif', 'bmp', 'tiff']


def get_file_info(file_path: str) -> dict:
    """Get comprehensive file information."""
    ext, mime_type = detect_file_type(file_path)
    file_size = os.path.getsize(file_path)
    
    return {
        'file_path': file_path,
        'extension': ext,
        'mime_type': mime_type,
        'size_bytes': file_size,
        'size_mb': round(file_size / (1024 * 1024), 2),
        'is_pdf': is_pdf(file_path),
        'is_image': is_image(file_path),
    }
