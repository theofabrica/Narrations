"""
Higgsfield API client for image and video generation.
"""
import httpx
import time
from typing import Dict, Any, Optional
from app.config.settings import settings
from app.utils.errors import ProviderError
from app.utils.logging import logger


class HiggsfieldClient:
    """Client for Higgsfield API."""
    
    def __init__(self):
        """Initialize Higgsfield client."""
        self.api_key = settings.HIGGSFIELD_API_KEY
        self.api_key_id = settings.HIGGSFIELD_API_KEY_ID
        self.api_key_secret = settings.HIGGSFIELD_API_KEY_SECRET
        self.base_url = settings.HIGGSFIELD_BASE_URL
        self.timeout = settings.HIGGSFIELD_TIMEOUT
        self.retries = settings.HIGGSFIELD_RETRIES
        self.polling_interval = settings.HIGGSFIELD_POLLING_INTERVAL
        
        if not (self.api_key or (self.api_key_id and self.api_key_secret)):
            logger.warning("HIGGSFIELD_API_KEY or (HIGGSFIELD_API_KEY_ID/SECRET) not set")
    
    def _get_headers(self) -> Dict[str, str]:
        """Get request headers with authentication."""
        headers = {
            "Content-Type": "application/json"
        }
        # Preferred auth: Key <id>:<secret> (per docs)
        if self.api_key_id and self.api_key_secret:
            headers["Authorization"] = f"Key {self.api_key_id}:{self.api_key_secret}"
        elif self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        return headers
    
    def _request(
        self,
        method: str,
        endpoint: str,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Make HTTP request to Higgsfield API.
        
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
                    error_msg = f"Higgsfield API error: {e.response.status_code}"
                    try:
                        error_data = e.response.json()
                        error_msg = error_data.get("error", {}).get("message", error_msg)
                        if not error_msg:
                            error_msg = error_data.get("message", error_msg)
                    except:
                        error_msg = e.response.text or error_msg
                    
                    raise ProviderError(
                        provider="higgsfield",
                        message=error_msg,
                        details={
                            "status_code": e.response.status_code,
                            "endpoint": endpoint
                        },
                        retryable=e.response.status_code >= 500
                    )
                # Retry on server error
                logger.warning(f"Higgsfield API error (attempt {attempt + 1}/{self.retries}): {e}")
                continue
            
            except httpx.RequestError as e:
                if attempt == self.retries - 1:
                    raise ProviderError(
                        provider="higgsfield",
                        message=f"Request failed: {str(e)}",
                        details={"endpoint": endpoint},
                        retryable=True
                    )
                logger.warning(f"Higgsfield request error (attempt {attempt + 1}/{self.retries}): {e}")
                continue
        
        raise ProviderError(
            provider="higgsfield",
            message="Request failed after retries",
            details={"endpoint": endpoint},
            retryable=True
        )
    
    def generate_image(
        self,
        prompt: str,
        model: Optional[str] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Generate image from prompt.
        
        Args:
            prompt: Image generation prompt
            model: Model name (optional)
            **kwargs: Additional parameters (width, height, steps, etc.)
        
        Returns:
            Response with image data or job information
        """
        endpoint = "images/generate"
        payload = {
            "prompt": prompt,
            **kwargs
        }
        if model:
            payload["model"] = model
        return self._request("POST", endpoint, json=payload)
    
    def generate_video(
        self,
        prompt: Optional[str] = None,
        image_url: Optional[str] = None,
        model: Optional[str] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Generate video from prompt or image.
        
        Args:
            prompt: Video generation prompt (optional if image_url provided)
            image_url: URL of source image (optional if prompt provided)
            model: Model name (optional)
            **kwargs: Additional parameters (duration, fps, etc.)
        
        Returns:
            Response with video data or job information
        """
        endpoint = "videos/generate"
        payload = {**kwargs}
        
        if prompt:
            payload["prompt"] = prompt
        if image_url:
            payload["image_url"] = image_url
        if model:
            payload["model"] = model
        
        if not prompt and not image_url:
            raise ProviderError(
                provider="higgsfield",
                message="Either prompt or image_url is required",
                retryable=False
            )
        
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
    
    def poll_job(
        self,
        job_id: str,
        max_wait: Optional[int] = None,
        poll_interval: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Poll a job until completion or failure.
        
        Args:
            job_id: Job ID
            max_wait: Maximum time to wait in seconds (None = no limit)
            poll_interval: Time between polls in seconds (default: self.polling_interval)
        
        Returns:
            Final job status
        """
        poll_interval = poll_interval or self.polling_interval
        start_time = time.time()
        
        while True:
            status = self.get_job_status(job_id)
            job_status = status.get("status", "").lower()
            
            # Check if job is complete
            if job_status in ["completed", "failed", "error"]:
                return status
            
            # Check timeout
            if max_wait and (time.time() - start_time) >= max_wait:
                logger.warning(f"Job {job_id} polling timeout after {max_wait}s")
                return status
            
            # Wait before next poll
            time.sleep(poll_interval)


# Global client instance
_client: Optional[HiggsfieldClient] = None


def get_client() -> HiggsfieldClient:
    """Get or create Higgsfield client instance."""
    global _client
    if _client is None:
        _client = HiggsfieldClient()
    return _client
