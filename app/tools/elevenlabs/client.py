"""
ElevenLabs API client for voice, music, and sound effects generation.
"""
import httpx
from typing import Dict, Any, Optional
from app.config.settings import settings
from app.utils.errors import ProviderError
from app.utils.logging import logger


class ElevenLabsClient:
    """Client for ElevenLabs API."""
    
    def __init__(self):
        """Initialize ElevenLabs client."""
        self.api_key = settings.ELEVENLABS_API_KEY
        self.base_url = settings.ELEVENLABS_BASE_URL
        self.timeout = settings.ELEVENLABS_TIMEOUT
        self.retries = settings.ELEVENLABS_RETRIES
        
        if not self.api_key:
            logger.warning("ELEVENLABS_API_KEY not set")
    
    def _get_headers(self) -> Dict[str, str]:
        """Get request headers with authentication."""
        headers = {
            "Content-Type": "application/json"
        }
        if self.api_key:
            headers["xi-api-key"] = self.api_key
        return headers
    
    def _request(
        self,
        method: str,
        endpoint: str,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Make HTTP request to ElevenLabs API.
        
        Args:
            method: HTTP method (GET, POST, etc.)
            endpoint: API endpoint (relative to base_url)
            **kwargs: Additional arguments for httpx request
        
        Returns:
            Response JSON data
        
        Raises:
            ProviderError: If request fails
        """
        url = f"{self.base_url.rstrip('/')}/{endpoint.lstrip('/')}"
        headers = self._get_headers()
        
        for attempt in range(self.retries):
            try:
                with httpx.Client(timeout=self.timeout) as client:
                    response = client.request(
                        method=method,
                        url=url,
                        headers=headers,
                        **kwargs
                    )
                    response.raise_for_status()
                    return response.json() if response.content else {}
            
            except httpx.HTTPStatusError as e:
                if e.response.status_code < 500 or attempt == self.retries - 1:
                    # Client error or last retry
                    error_msg = f"ElevenLabs API error: {e.response.status_code}"
                    try:
                        error_data = e.response.json()
                        error_msg = error_data.get("detail", {}).get("message", error_msg)
                    except:
                        error_msg = e.response.text or error_msg
                    
                    raise ProviderError(
                        provider="elevenlabs",
                        message=error_msg,
                        details={
                            "status_code": e.response.status_code,
                            "endpoint": endpoint
                        },
                        retryable=e.response.status_code >= 500
                    )
                # Retry on server error
                logger.warning(f"ElevenLabs API error (attempt {attempt + 1}/{self.retries}): {e}")
                continue
            
            except httpx.RequestError as e:
                if attempt == self.retries - 1:
                    raise ProviderError(
                        provider="elevenlabs",
                        message=f"Request failed: {str(e)}",
                        details={"endpoint": endpoint},
                        retryable=True
                    )
                logger.warning(f"ElevenLabs request error (attempt {attempt + 1}/{self.retries}): {e}")
                continue
        
        raise ProviderError(
            provider="elevenlabs",
            message="Request failed after retries",
            details={"endpoint": endpoint},
            retryable=True
        )
    
    def text_to_speech(
        self,
        text: str,
        voice_id: str = "21m00Tcm4TlvDq8ikWAM",
        model_id: str = "eleven_multilingual_v2",
        **kwargs
    ) -> Dict[str, Any]:
        """
        Generate speech from text.
        
        Args:
            text: Text to convert to speech
            voice_id: Voice ID to use
            model_id: Model ID to use
            **kwargs: Additional parameters (stability, similarity_boost, etc.)
        
        Returns:
            Response with audio data or job information
        """
        endpoint = f"text-to-speech/{voice_id}"
        payload = {
            "text": text,
            "model_id": model_id,
            **kwargs
        }
        return self._request("POST", endpoint, json=payload)
    
    def generate_music(
        self,
        prompt: str,
        duration: Optional[int] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Generate music from prompt.
        
        Args:
            prompt: Music generation prompt
            duration: Duration in seconds (optional)
            **kwargs: Additional parameters
        
        Returns:
            Response with audio data or job information
        """
        endpoint = "music-generation"
        payload = {
            "prompt": prompt,
            **kwargs
        }
        if duration:
            payload["duration"] = duration
        return self._request("POST", endpoint, json=payload)
    
    def generate_sound_effect(
        self,
        prompt: str,
        duration: Optional[int] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Generate sound effect from prompt.
        
        Args:
            prompt: Sound effect generation prompt
            duration: Duration in seconds (optional)
            **kwargs: Additional parameters
        
        Returns:
            Response with audio data or job information
        """
        endpoint = "sound-generation"
        payload = {
            "prompt": prompt,
            **kwargs
        }
        if duration:
            payload["duration"] = duration
        return self._request("POST", endpoint, json=payload)
    
    def get_job_status(self, job_id: str) -> Dict[str, Any]:
        """
        Get status of an async job.
        
        Args:
            job_id: Job ID
        
        Returns:
            Job status information
        """
        endpoint = f"jobs/{job_id}"
        return self._request("GET", endpoint)


# Global client instance
_client: Optional[ElevenLabsClient] = None


def get_client() -> ElevenLabsClient:
    """Get or create ElevenLabs client instance."""
    global _client
    if _client is None:
        _client = ElevenLabsClient()
    return _client
