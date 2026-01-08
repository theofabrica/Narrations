"""
Tests for ElevenLabs handlers (Phase 2).
"""
import pytest
from unittest.mock import Mock, patch, MagicMock
from fastapi.testclient import TestClient
from app.main import app
from app.tools.elevenlabs.client import ElevenLabsClient
from app.tools.elevenlabs import voice, music, soundfx
from app.utils.errors import ValidationError, ProviderError


client = TestClient(app)


class TestElevenLabsClient:
    """Tests for ElevenLabs client."""
    
    def test_client_initialization(self):
        """Test client initialization."""
        client = ElevenLabsClient()
        # Just verify client can be created
        assert client is not None
        assert client.base_url == "https://api.elevenlabs.io/v1"
        # API key may be None if not set in environment
    
    @patch("httpx.Client")
    def test_text_to_speech_success(self, mock_client_class):
        """Test successful text to speech request."""
        mock_response = Mock()
        mock_response.json.return_value = {"audio_url": "https://example.com/audio.mp3"}
        mock_response.status_code = 200
        mock_response.content = b'{"audio_url": "https://example.com/audio.mp3"}'
        
        mock_client = MagicMock()
        mock_client.request.return_value = mock_response
        mock_client_class.return_value.__enter__.return_value = mock_client
        
        client = ElevenLabsClient()
        result = client.text_to_speech("Hello world")
        
        assert "audio_url" in result
        mock_client.request.assert_called_once()
    
    @patch("httpx.Client")
    def test_text_to_speech_error(self, mock_client_class):
        """Test text to speech with API error."""
        import httpx
        
        mock_response = Mock()
        mock_response.status_code = 400
        mock_response.json.return_value = {"detail": {"message": "Invalid request"}}
        mock_response.text = "Bad Request"
        mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "Bad Request", request=Mock(), response=mock_response
        )
        
        mock_client = MagicMock()
        mock_client.request.return_value = mock_response
        mock_client_class.return_value.__enter__.return_value = mock_client
        
        client = ElevenLabsClient()
        with pytest.raises(ProviderError) as exc_info:
            client.text_to_speech("Hello")
        
        assert "ELEVENLABS_ERROR" in exc_info.value.code or "elevenlabs" in exc_info.value.code.lower()


class TestElevenLabsHandlers:
    """Tests for ElevenLabs handlers."""
    
    def test_voice_missing_text(self):
        """Test voice generation with missing text."""
        with pytest.raises(ValidationError):
            voice.generate_voice({})
    
    @patch("app.tools.elevenlabs.voice.get_client")
    def test_voice_generation_success(self, mock_get_client):
        """Test successful voice generation."""
        mock_client = Mock()
        mock_client.text_to_speech.return_value = {
            "audio_url": "https://example.com/audio.mp3"
        }
        mock_get_client.return_value = mock_client
        
        result = voice.generate_voice({"text": "Hello world"})
        
        assert result["status"] == "completed"
        assert result["provider"] == "elevenlabs"
        assert len(result["links"]) > 0
        assert result["links"][0]["asset_type"] == "voice"
    
    @patch("app.tools.elevenlabs.voice.get_client")
    def test_voice_generation_async(self, mock_get_client):
        """Test async voice generation (job)."""
        mock_client = Mock()
        mock_client.text_to_speech.return_value = {
            "job_id": "job_123"
        }
        mock_get_client.return_value = mock_client
        
        result = voice.generate_voice({"text": "Hello world"})
        
        assert result["status"] == "pending"
        assert result["job_id"] == "job_123"
        assert len(result["links"]) == 0
    
    def test_music_missing_prompt(self):
        """Test music generation with missing prompt."""
        with pytest.raises(ValidationError):
            music.generate_music({})
    
    @patch("app.tools.elevenlabs.music.get_client")
    def test_music_generation_success(self, mock_get_client):
        """Test successful music generation."""
        mock_client = Mock()
        mock_client.generate_music.return_value = {
            "audio_url": "https://example.com/music.mp3"
        }
        mock_get_client.return_value = mock_client
        
        result = music.generate_music({"prompt": "Upbeat electronic music"})
        
        assert result["status"] == "completed"
        assert result["provider"] == "elevenlabs"
        assert result["model"] == "music-generation"
    
    def test_soundfx_missing_prompt(self):
        """Test sound effect generation with missing prompt."""
        with pytest.raises(ValidationError):
            soundfx.generate_soundfx({})
    
    @patch("app.tools.elevenlabs.soundfx.get_client")
    def test_soundfx_generation_success(self, mock_get_client):
        """Test successful sound effect generation."""
        mock_client = Mock()
        mock_client.generate_sound_effect.return_value = {
            "audio_url": "https://example.com/sfx.mp3"
        }
        mock_get_client.return_value = mock_client
        
        result = soundfx.generate_soundfx({"prompt": "Thunder sound"})
        
        assert result["status"] == "completed"
        assert result["provider"] == "elevenlabs"
        assert result["model"] == "sound-generation"


class TestElevenLabsEndpoints:
    """Tests for ElevenLabs MCP endpoints."""
    
    @patch("app.tools.elevenlabs.voice.get_client")
    def test_elevenlabs_voice_endpoint(self, mock_get_client):
        """Test ElevenLabs voice endpoint."""
        mock_client = Mock()
        mock_client.text_to_speech.return_value = {
            "audio_url": "https://example.com/audio.mp3"
        }
        mock_get_client.return_value = mock_client
        
        response = client.post(
            "/mcp",
            json={
                "action": "elevenlabs_voice",
                "payload": {
                    "text": "Hello world",
                    "voice_id": "test_voice"
                }
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert data["action"] == "elevenlabs_voice"
        assert data["data"]["status"] == "completed"
    
    @patch("app.tools.elevenlabs.music.get_client")
    def test_elevenlabs_music_endpoint(self, mock_get_client):
        """Test ElevenLabs music endpoint."""
        mock_client = Mock()
        mock_client.generate_music.return_value = {
            "audio_url": "https://example.com/music.mp3"
        }
        mock_get_client.return_value = mock_client
        
        response = client.post(
            "/mcp",
            json={
                "action": "elevenlabs_music",
                "payload": {
                    "prompt": "Upbeat electronic music"
                }
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert data["action"] == "elevenlabs_music"
    
    @patch("app.tools.elevenlabs.soundfx.get_client")
    def test_elevenlabs_soundfx_endpoint(self, mock_get_client):
        """Test ElevenLabs soundfx endpoint."""
        mock_client = Mock()
        mock_client.generate_sound_effect.return_value = {
            "audio_url": "https://example.com/sfx.mp3"
        }
        mock_get_client.return_value = mock_client
        
        response = client.post(
            "/mcp",
            json={
                "action": "elevenlabs_soundfx",
                "payload": {
                    "prompt": "Thunder sound"
                }
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert data["action"] == "elevenlabs_soundfx"
