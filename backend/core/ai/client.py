"""
OpenAI Unified Client with Retry Logic, Timeouts, and Error Handling

Features:
- Exponential backoff retries
- Timeout management
- Request/response logging with redaction
- Comprehensive error categorization
- Rate limit handling
"""
import logging
import time
from typing import Optional, Dict, Any
import json

try:
    from openai import OpenAI, APIError, RateLimitError as OpenAIRateLimitError, APITimeoutError
except ImportError:
    raise ImportError("openai package required. Install with: pip install openai")

from .constants import (
    OPENAI_API_KEY,
    OPENAI_MODEL,
    OPENAI_VISION_MODEL,
    OPENAI_TIMEOUT,
    OPENAI_MAX_TOKENS,
    OPENAI_TEMPERATURE,
    MAX_RETRIES,
    INITIAL_RETRY_DELAY,
    MAX_RETRY_DELAY,
    EXPONENTIAL_BASE,
)
from .errors import AIAPIError, RateLimitError as RateLimitErrorCustom, TimeoutError as TimeoutErrorCustom
from .utils import redact_sensitive_data

logger = logging.getLogger(__name__)


class OpenAIClient:
    """Unified OpenAI client with production-grade reliability."""
    
    def __init__(
        self,
        api_key: str = OPENAI_API_KEY,
        timeout: int = OPENAI_TIMEOUT,
        max_retries: int = MAX_RETRIES
    ):
        """Initialize OpenAI client."""
        if not api_key:
            raise ValueError("OPENAI_API_KEY environment variable not set")
        
        self.client = OpenAI(api_key=api_key, timeout=timeout)
        self.timeout = timeout
        self.max_retries = max_retries
        self.model = OPENAI_MODEL
        self.vision_model = OPENAI_VISION_MODEL
        self.max_tokens = OPENAI_MAX_TOKENS
        self.temperature = OPENAI_TEMPERATURE
        
        logger.info(f"OpenAI client initialized with model={self.model}, timeout={timeout}s")
    
    def vision_extract(
        self,
        image_base64: str,
        prompt: str,
        model: Optional[str] = None,
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None
    ) -> str:
        """
        Extract text/data from image using vision model.
        
        Args:
            image_base64: Base64 encoded image
            prompt: Detailed extraction instructions
            model: Model to use (default: OPENAI_VISION_MODEL)
            max_tokens: Max tokens in response
            temperature: Creativity 0-1 (default: 0.3)
            
        Returns:
            API response text
            
        Raises:
            AIAPIError: OpenAI API error
            RateLimitError: Rate limit exceeded
            TimeoutError: Request timeout
        """
        model = model or self.vision_model
        max_tokens = max_tokens or self.max_tokens
        temperature = temperature if temperature is not None else self.temperature
        
        return self._call_with_retry(
            method='vision',
            model=model,
            image_base64=image_base64,
            prompt=prompt,
            max_tokens=max_tokens,
            temperature=temperature
        )
    
    def text_extract(
        self,
        text: str,
        prompt: str,
        model: Optional[str] = None,
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None
    ) -> str:
        """
        Extract structured data from text.
        
        Args:
            text: Input text to analyze
            prompt: Analysis instructions
            model: Model to use
            max_tokens: Max tokens in response
            temperature: Creativity 0-1
            
        Returns:
            API response text
        """
        model = model or self.model
        max_tokens = max_tokens or self.max_tokens
        temperature = temperature if temperature is not None else self.temperature
        
        full_prompt = f"{prompt}\n\n--- TEXT TO ANALYZE ---\n{text}"
        
        return self._call_with_retry(
            method='text',
            model=model,
            prompt=full_prompt,
            max_tokens=max_tokens,
            temperature=temperature
        )
    
    def text_chat(
        self,
        messages: list,
        model: Optional[str] = None,
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None
    ) -> str:
        """
        Chat-based completion for flexible interactions.
        
        Args:
            messages: List of message dicts with 'role' and 'content'
            model: Model to use
            max_tokens: Max tokens
            temperature: Creativity
            
        Returns:
            Response text
        """
        model = model or self.model
        max_tokens = max_tokens or self.max_tokens
        temperature = temperature if temperature is not None else self.temperature
        
        return self._call_with_retry(
            method='chat',
            model=model,
            messages=messages,
            max_tokens=max_tokens,
            temperature=temperature
        )
    
    def _call_with_retry(
        self,
        method: str,
        model: str,
        max_tokens: int,
        temperature: float,
        **kwargs
    ) -> str:
        """
        Execute API call with exponential backoff retry logic.
        
        Args:
            method: 'vision', 'text', or 'chat'
            model: Model name
            max_tokens: Token limit
            temperature: Creativity parameter
            **kwargs: Additional parameters for the method
            
        Returns:
            API response text
            
        Raises:
            AIAPIError: If all retries exhausted
        """
        last_error = None
        
        for attempt in range(self.max_retries):
            try:
                logger.debug(f"OpenAI API call (attempt {attempt + 1}/{self.max_retries}): "
                           f"method={method}, model={model}")
                
                response = self._execute_api_call(
                    method=method,
                    model=model,
                    max_tokens=max_tokens,
                    temperature=temperature,
                    **kwargs
                )
                
                logger.debug(f"OpenAI API call succeeded: {redact_sensitive_data(str(response)[:100])}")
                return response
            
            except OpenAIRateLimitError as e:
                retry_after = int(e.response.headers.get('retry-after', 60)) if hasattr(e, 'response') else 60
                logger.warning(f"Rate limit hit. Retry after {retry_after}s")
                raise RateLimitErrorCustom(
                    f"OpenAI rate limit exceeded",
                    retry_after=retry_after
                )
            
            except APITimeoutError as e:
                logger.warning(f"Timeout on attempt {attempt + 1}: {e}")
                last_error = e
                
                if attempt < self.max_retries - 1:
                    wait_time = self._calculate_backoff(attempt)
                    logger.info(f"Retrying in {wait_time}s...")
                    time.sleep(wait_time)
                else:
                    raise TimeoutErrorCustom(
                        f"OpenAI request timed out after {self.timeout}s",
                        timeout_seconds=self.timeout
                    )
            
            except APIError as e:
                logger.error(f"OpenAI API error on attempt {attempt + 1}: {e}")
                last_error = e
                
                # Don't retry on client errors (400, 401, 403)
                if hasattr(e, 'status_code') and 400 <= e.status_code < 500:
                    raise AIAPIError(
                        str(e),
                        status_code=getattr(e, 'status_code', None)
                    )
                
                if attempt < self.max_retries - 1:
                    wait_time = self._calculate_backoff(attempt)
                    logger.info(f"Retrying in {wait_time}s...")
                    time.sleep(wait_time)
            
            except Exception as e:
                logger.error(f"Unexpected error in OpenAI call: {e}")
                last_error = e
                raise AIAPIError(f"Unexpected error: {str(e)}")
        
        # All retries exhausted
        raise AIAPIError(f"OpenAI API failed after {self.max_retries} attempts: {str(last_error)}")
    
    def _execute_api_call(
        self,
        method: str,
        model: str,
        max_tokens: int,
        temperature: float,
        **kwargs
    ) -> str:
        """Execute the actual API call based on method type."""
        
        if method == 'vision':
            image_base64 = kwargs.pop('image_base64')
            prompt = kwargs.pop('prompt')
            
            response = self.client.chat.completions.create(
                model=model,
                max_tokens=max_tokens,
                temperature=temperature,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/jpeg;base64,{image_base64}",
                                },
                            },
                            {
                                "type": "text",
                                "text": prompt
                            }
                        ],
                    }
                ],
            )
        
        elif method == 'text':
            prompt = kwargs.pop('prompt')
            
            response = self.client.chat.completions.create(
                model=model,
                max_tokens=max_tokens,
                temperature=temperature,
                messages=[
                    {"role": "user", "content": prompt}
                ]
            )
        
        elif method == 'chat':
            messages = kwargs.pop('messages')
            
            response = self.client.chat.completions.create(
                model=model,
                max_tokens=max_tokens,
                temperature=temperature,
                messages=messages
            )
        
        else:
            raise ValueError(f"Unknown method: {method}")
        
        # Extract text from response
        return response.choices[0].message.content if response.choices else ""
    
    def _calculate_backoff(self, attempt: int) -> float:
        """Calculate exponential backoff with jitter."""
        import random
        
        delay = min(
            INITIAL_RETRY_DELAY * (EXPONENTIAL_BASE ** attempt),
            MAX_RETRY_DELAY
        )
        jitter = random.uniform(0, delay * 0.1)
        return delay + jitter


# Global client instance
_client = None


def get_openai_client() -> OpenAIClient:
    """Get or create global OpenAI client."""
    global _client
    if _client is None:
        _client = OpenAIClient()
    return _client
