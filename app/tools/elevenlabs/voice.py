"""
ElevenLabs voice (TTS) handler.
"""
from typing import Dict, Any
from app.tools.elevenlabs.client import get_client
from app.utils.ids import generate_job_id, generate_asset_id, generate_timestamp
from app.utils.errors import ValidationError
from app.utils.logging import logger
from app.utils.media_storage import get_project_name, process_asset_links
from app.mcp.schemas import JobStatus, AssetLink


def generate_voice(payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    Generate voice from text using ElevenLabs TTS.
    
    Expected payload:
        - text: str (required) - Text to convert to speech
        - voice_id: str (optional) - Voice ID (default: "21m00Tcm4TlvDq8ikWAM")
        - model_id: str (optional) - Model ID (default: "eleven_multilingual_v2")
        - stability: float (optional) - Stability parameter
        - similarity_boost: float (optional) - Similarity boost parameter
        - style: float (optional) - Style parameter
        - use_speaker_boost: bool (optional) - Use speaker boost
    
    Returns:
        Job status with asset links
    """
    # Validate payload
    if not payload.get("text"):
        raise ValidationError("text is required")
    
    text = payload["text"]
    voice_id = payload.get("voice_id", "21m00Tcm4TlvDq8ikWAM")
    model_id = payload.get("model_id", "eleven_multilingual_v2")
    
    # Get project name from payload or trace
    trace = payload.get("_trace")
    project_name = get_project_name(payload, trace)
    
    # Generate IDs
    job_id = generate_job_id("elevenlabs")
    asset_id = generate_asset_id("elevenlabs", "voice")
    created_at = generate_timestamp()
    
    logger.info(f"Generating voice: job_id={job_id}, voice_id={voice_id}, text_length={len(text)}")
    
    try:
        # Call ElevenLabs API
        client = get_client()
        
        # Extract optional parameters
        optional_params = {}
        for key in ["stability", "similarity_boost", "style", "use_speaker_boost"]:
            if key in payload:
                optional_params[key] = payload[key]
        
        response = client.text_to_speech(
            text=text,
            voice_id=voice_id,
            model_id=model_id,
            **optional_params
        )
        
        # Check if response is async (job) or sync (audio data)
        if "job_id" in response:
            # Async job
            job_id = response["job_id"]
            return {
                "job_id": job_id,
                "status": "pending",
                "provider": "elevenlabs",
                "model": model_id,
                "params": {
                    "voice_id": voice_id,
                    "text_length": len(text),
                    **optional_params
                },
                "created_at": created_at,
                "completed_at": None,
                "links": [],
                "error": None
            }
        else:
            # Synchronous response with audio
            audio_url = response.get("audio_url") or response.get("url")
            if not audio_url and "audio" in response:
                # Audio data in response - would need to be saved/uploaded
                # For now, we'll treat it as a completed job
                audio_url = f"data:audio/mpeg;base64,{response.get('audio', '')[:50]}..."
            
            completed_at = generate_timestamp()
            
            asset_link = AssetLink(
                url=audio_url or "pending",
                asset_id=asset_id,
                asset_type="voice",
                provider="elevenlabs",
                created_at=completed_at
            )
            
            # Process links (download and store if enabled)
            links = process_asset_links([asset_link], project_name, "audio", completed_at)
            
            return {
                "job_id": job_id,
                "status": "completed",
                "provider": "elevenlabs",
                "model": model_id,
                "params": {
                    "voice_id": voice_id,
                    "text_length": len(text),
                    **optional_params
                },
                "created_at": created_at,
                "completed_at": completed_at,
                "links": links,
                "error": None
            }
    
    except Exception as e:
        logger.error(f"Error generating voice: {e}", exc_info=True)
        raise
