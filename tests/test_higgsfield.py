"""
Tests for Higgsfield handlers (Phase 2).
"""
import pytest
from unittest.mock import Mock, patch, MagicMock
from fastapi.testclient import TestClient
from app.main import app
from app.tools.higgsfield.client import HiggsfieldClient
from app.tools.higgsfield import image, video
from app.utils.errors import ValidationError, ProviderError


client = TestClient(app)


class TestHiggsfieldClient:
    """Tests for Higgsfield client."""
    
    def test_client_initialization(self):
        """Test client initialization."""
        client = HiggsfieldClient()
        # Just verify client can be created
        assert client is not None
        assert client.base_url == "https://api.higgsfield.ai"
        # API key may be None if not set in environment
    
    @patch("httpx.Client")
    def test_generate_image_success(self, mock_client_class):
        """Test successful image generation request."""
        mock_response = Mock()
        mock_response.json.return_value = {"image_url": "https://example.com/image.png"}
        mock_response.status_code = 200
        mock_response.content = b'{"image_url": "https://example.com/image.png"}'
        
        mock_client = MagicMock()
        mock_client.request.return_value = mock_response
        mock_client_class.return_value.__enter__.return_value = mock_client
        
        client = HiggsfieldClient()
        result = client.generate_image("A beautiful sunset")
        
        assert "image_url" in result
        mock_client.request.assert_called_once()
    
    @patch("httpx.Client")
    def test_generate_video_success(self, mock_client_class):
        """Test successful video generation request."""
        mock_response = Mock()
        mock_response.json.return_value = {"job_id": "job_123"}
        mock_response.status_code = 200
        mock_response.content = b'{"job_id": "job_123"}'
        
        mock_client = MagicMock()
        mock_client.request.return_value = mock_response
        mock_client_class.return_value.__enter__.return_value = mock_client
        
        client = HiggsfieldClient()
        result = client.generate_video(prompt="A dancing cat")
        
        assert "job_id" in result


class TestHiggsfieldHandlers:
    """Tests for Higgsfield handlers."""
    
    def test_image_missing_prompt(self):
        """Test image generation with missing prompt."""
        with pytest.raises(ValidationError):
            image.generate_image({})
    
    @patch("app.tools.higgsfield.image.get_client")
    def test_image_generation_success(self, mock_get_client):
        """Test successful image generation."""
        mock_client = Mock()
        mock_client.generate_image.return_value = {
            "image_url": "https://example.com/image.png"
        }
        mock_get_client.return_value = mock_client
        
        result = image.generate_image({"prompt": "A beautiful sunset"})
        
        assert result["status"] == "completed"
        assert result["provider"] == "higgsfield"
        assert len(result["links"]) > 0
        assert result["links"][0]["asset_type"] == "image"
    
    @patch("app.tools.higgsfield.image.get_client")
    def test_image_generation_async(self, mock_get_client):
        """Test async image generation (job)."""
        mock_client = Mock()
        mock_client.generate_image.return_value = {
            "job_id": "job_123"
        }
        mock_get_client.return_value = mock_client
        
        result = image.generate_image({"prompt": "A beautiful sunset"})
        
        assert result["status"] == "pending"
        assert result["job_id"] == "job_123"
    
    @patch("app.tools.higgsfield.image.get_client")
    def test_image_generation_with_polling(self, mock_get_client):
        """Test image generation with polling."""
        mock_client = Mock()
        mock_client.generate_image.return_value = {
            "job_id": "job_123"
        }
        mock_client.poll_job.return_value = {
            "status": "completed",
            "result_url": "https://example.com/image.png"
        }
        mock_get_client.return_value = mock_client
        
        result = image.generate_image({
            "prompt": "A beautiful sunset",
            "wait_for_completion": True
        })
        
        assert result["status"] == "completed"
        assert len(result["links"]) > 0
        mock_client.poll_job.assert_called_once_with("job_123")
    
    def test_video_missing_prompt_and_image(self):
        """Test video generation with missing prompt and image_url."""
        with pytest.raises(ValidationError):
            video.generate_video({})
    
    @patch("app.tools.higgsfield.video.get_client")
    def test_video_generation_with_prompt(self, mock_get_client):
        """Test video generation with prompt."""
        mock_client = Mock()
        mock_client.generate_video.return_value = {
            "job_id": "job_123"
        }
        mock_get_client.return_value = mock_client
        
        result = video.generate_video({"prompt": "A dancing cat"})
        
        assert result["status"] == "pending"
        assert result["provider"] == "higgsfield"
    
    @patch("app.tools.higgsfield.video.get_client")
    def test_video_generation_with_image_url(self, mock_get_client):
        """Test video generation with image_url."""
        mock_client = Mock()
        mock_client.generate_video.return_value = {
            "job_id": "job_123"
        }
        mock_get_client.return_value = mock_client
        
        result = video.generate_video({
            "image_url": "https://example.com/image.png"
        })
        
        assert result["status"] == "pending"
        assert result["provider"] == "higgsfield"


class TestHiggsfieldEndpoints:
    """Tests for Higgsfield MCP endpoints."""
    
    @patch("app.tools.higgsfield.image.get_client")
    def test_higgsfield_image_endpoint(self, mock_get_client):
        """Test Higgsfield image endpoint."""
        mock_client = Mock()
        mock_client.generate_image.return_value = {
            "image_url": "https://example.com/image.png"
        }
        mock_get_client.return_value = mock_client
        
        response = client.post(
            "/mcp",
            json={
                "action": "higgsfield_image",
                "payload": {
                    "prompt": "A beautiful sunset"
                }
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert data["action"] == "higgsfield_image"
        assert data["data"]["status"] == "completed"
    
    @patch("app.tools.higgsfield.video.get_client")
    def test_higgsfield_video_endpoint(self, mock_get_client):
        """Test Higgsfield video endpoint."""
        mock_client = Mock()
        mock_client.generate_video.return_value = {
            "job_id": "job_123"
        }
        mock_get_client.return_value = mock_client
        
        response = client.post(
            "/mcp",
            json={
                "action": "higgsfield_video",
                "payload": {
                    "prompt": "A dancing cat"
                }
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert data["action"] == "higgsfield_video"
        assert data["data"]["status"] == "pending"
    
    @patch("app.tools.higgsfield.client.get_client")
    def test_check_job_status_endpoint(self, mock_get_client):
        """Test check_job_status endpoint."""
        mock_client = Mock()
        mock_client.get_job_status.return_value = {
            "status": "completed",
            "result_url": "https://example.com/image.png"
        }
        mock_get_client.return_value = mock_client
        
        response = client.post(
            "/mcp",
            json={
                "action": "check_job_status",
                "payload": {
                    "job_id": "job_123",
                    "provider": "higgsfield"
                }
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert data["action"] == "check_job_status"
