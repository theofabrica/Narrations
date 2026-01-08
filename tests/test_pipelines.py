"""
Tests for pipeline handlers (Phase 3).
"""
import pytest
from unittest.mock import Mock, patch
from fastapi.testclient import TestClient
from app.main import app
from app.pipelines.image_to_video import image_to_video
from app.pipelines.audio_stack import audio_stack
from app.utils.errors import ValidationError


client = TestClient(app)


class TestImageToVideoPipeline:
    """Tests for image_to_video pipeline."""
    
    def test_missing_prompt(self):
        """Test pipeline with missing prompt."""
        with pytest.raises(ValidationError):
            image_to_video({})
    
    @patch("app.pipelines.image_to_video.image.generate_image")
    @patch("app.pipelines.image_to_video.video.generate_video")
    def test_pipeline_success(self, mock_video, mock_image):
        """Test successful pipeline execution."""
        # Mock image generation
        mock_image.return_value = {
            "job_id": "img_job_123",
            "status": "completed",
            "provider": "higgsfield",
            "links": [{
                "url": "https://example.com/image.png",
                "asset_id": "img_asset_123",
                "asset_type": "image",
                "provider": "higgsfield",
                "created_at": "2024-01-01T00:00:00Z"
            }]
        }
        
        # Mock video generation
        mock_video.return_value = {
            "job_id": "vid_job_123",
            "status": "completed",
            "provider": "higgsfield",
            "links": [{
                "url": "https://example.com/video.mp4",
                "asset_id": "vid_asset_123",
                "asset_type": "video",
                "provider": "higgsfield",
                "created_at": "2024-01-01T00:00:01Z"
            }]
        }
        
        result = image_to_video({
            "prompt": "A beautiful sunset",
            "wait_for_completion": True
        })
        
        assert result["status"] == "completed"
        assert result["provider"] == "pipeline"
        assert result["model"] == "image_to_video"
        assert len(result["links"]) == 2
        assert len(result["steps"]) == 2
        assert result["steps"][0]["name"] == "image_generation"
        assert result["steps"][1]["name"] == "video_generation"
    
    @patch("app.pipelines.image_to_video.image.generate_image")
    def test_pipeline_image_failure(self, mock_image):
        """Test pipeline when image generation fails."""
        mock_image.return_value = {
            "job_id": "img_job_123",
            "status": "failed",
            "provider": "higgsfield",
            "error": {
                "code": "IMAGE_ERROR",
                "message": "Image generation failed"
            }
        }
        
        result = image_to_video({
            "prompt": "A beautiful sunset"
        })
        
        assert result["status"] == "failed"
        assert len(result["steps"]) == 1
        assert result["steps"][0]["status"] == "failed"


class TestAudioStackPipeline:
    """Tests for audio_stack pipeline."""
    
    def test_missing_all_audio_types(self):
        """Test pipeline with no audio types provided."""
        with pytest.raises(ValidationError):
            audio_stack({})
    
    def test_missing_voice_text(self):
        """Test pipeline with voice but missing text."""
        with pytest.raises(ValidationError):
            audio_stack({
                "voice": {}
            })
    
    def test_missing_music_prompt(self):
        """Test pipeline with music but missing prompt."""
        with pytest.raises(ValidationError):
            audio_stack({
                "music": {}
            })
    
    @patch("app.pipelines.audio_stack.voice.generate_voice")
    @patch("app.pipelines.audio_stack.music.generate_music")
    @patch("app.pipelines.audio_stack.soundfx.generate_soundfx")
    def test_pipeline_all_audio_types(self, mock_soundfx, mock_music, mock_voice):
        """Test pipeline with all audio types."""
        # Mock voice
        mock_voice.return_value = {
            "job_id": "voice_job_123",
            "status": "completed",
            "links": [{
                "url": "https://example.com/voice.mp3",
                "asset_id": "voice_asset_123",
                "asset_type": "voice",
                "provider": "elevenlabs",
                "created_at": "2024-01-01T00:00:00Z"
            }]
        }
        
        # Mock music
        mock_music.return_value = {
            "job_id": "music_job_123",
            "status": "completed",
            "links": [{
                "url": "https://example.com/music.mp3",
                "asset_id": "music_asset_123",
                "asset_type": "music",
                "provider": "elevenlabs",
                "created_at": "2024-01-01T00:00:01Z"
            }]
        }
        
        # Mock soundfx
        mock_soundfx.return_value = {
            "job_id": "sfx_job_123",
            "status": "completed",
            "links": [{
                "url": "https://example.com/sfx.mp3",
                "asset_id": "sfx_asset_123",
                "asset_type": "soundfx",
                "provider": "elevenlabs",
                "created_at": "2024-01-01T00:00:02Z"
            }]
        }
        
        result = audio_stack({
            "voice": {"text": "Hello world"},
            "music": {"prompt": "Upbeat music"},
            "soundfx": {"prompt": "Thunder sound"},
            "wait_for_completion": True
        })
        
        assert result["status"] == "completed"
        assert result["provider"] == "pipeline"
        assert result["model"] == "audio_stack"
        assert len(result["links"]) == 3
        assert len(result["steps"]) == 3
    
    @patch("app.pipelines.audio_stack.voice.generate_voice")
    def test_pipeline_voice_only(self, mock_voice):
        """Test pipeline with only voice."""
        mock_voice.return_value = {
            "job_id": "voice_job_123",
            "status": "completed",
            "links": [{
                "url": "https://example.com/voice.mp3",
                "asset_id": "voice_asset_123",
                "asset_type": "voice",
                "provider": "elevenlabs",
                "created_at": "2024-01-01T00:00:00Z"
            }]
        }
        
        result = audio_stack({
            "voice": {"text": "Hello world"}
        })
        
        assert result["status"] == "completed"
        assert len(result["steps"]) == 1
        assert result["steps"][0]["name"] == "voice_generation"


class TestPipelineEndpoints:
    """Tests for pipeline MCP endpoints."""
    
    @patch("app.pipelines.image_to_video.image.generate_image")
    @patch("app.pipelines.image_to_video.video.generate_video")
    def test_pipeline_image_to_video_endpoint(self, mock_video, mock_image):
        """Test image_to_video pipeline endpoint."""
        mock_image.return_value = {
            "job_id": "img_job_123",
            "status": "completed",
            "links": [{"url": "https://example.com/image.png", "asset_id": "img_123", "asset_type": "image", "provider": "higgsfield", "created_at": "2024-01-01T00:00:00Z"}]
        }
        mock_video.return_value = {
            "job_id": "vid_job_123",
            "status": "completed",
            "links": [{"url": "https://example.com/video.mp4", "asset_id": "vid_123", "asset_type": "video", "provider": "higgsfield", "created_at": "2024-01-01T00:00:01Z"}]
        }
        
        response = client.post(
            "/mcp",
            json={
                "action": "pipeline_image_to_video",
                "payload": {
                    "prompt": "A beautiful sunset"
                }
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert data["action"] == "pipeline_image_to_video"
        assert data["data"]["status"] == "completed"
    
    @patch("app.pipelines.audio_stack.voice.generate_voice")
    @patch("app.pipelines.audio_stack.music.generate_music")
    def test_pipeline_audio_stack_endpoint(self, mock_music, mock_voice):
        """Test audio_stack pipeline endpoint."""
        mock_voice.return_value = {
            "job_id": "voice_job_123",
            "status": "completed",
            "links": [{"url": "https://example.com/voice.mp3", "asset_id": "voice_123", "asset_type": "voice", "provider": "elevenlabs", "created_at": "2024-01-01T00:00:00Z"}]
        }
        mock_music.return_value = {
            "job_id": "music_job_123",
            "status": "completed",
            "links": [{"url": "https://example.com/music.mp3", "asset_id": "music_123", "asset_type": "music", "provider": "elevenlabs", "created_at": "2024-01-01T00:00:01Z"}]
        }
        
        response = client.post(
            "/mcp",
            json={
                "action": "pipeline_audio_stack",
                "payload": {
                    "voice": {"text": "Hello world"},
                    "music": {"prompt": "Upbeat music"}
                }
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert data["action"] == "pipeline_audio_stack"
        assert data["data"]["status"] == "completed"
