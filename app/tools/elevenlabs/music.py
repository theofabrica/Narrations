"""
ElevenLabs music generation handler.
"""
from typing import Dict, Any
from app.tools.elevenlabs.client import get_client
from app.utils.ids import generate_job_id, generate_asset_id, generate_timestamp
from app.utils.errors import ValidationError
from app.utils.logging import logger
from app.utils.media_storage import get_project_name, process_asset_links
from app.mcp.schemas import AssetLink


def generate_music(payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    Generate music from prompt using ElevenLabs.
    
    Expected payload:
        - prompt: str (required) - Music generation prompt
        - duration: int (optional) - Duration in seconds
        - temperature: float (optional) - Temperature parameter
        - seed: int (optional) - Random seed
    
    Returns:
        Job status with asset links
    """
    # Validate payload
    if not payload.get("prompt"):
        raise ValidationError("prompt is required")
    
    prompt = payload["prompt"]
    duration = payload.get("duration")
    
    # Get project name from payload or trace
    trace = payload.get("_trace")
    project_name = get_project_name(payload, trace)
    
    # Generate IDs
    job_id = generate_job_id("elevenlabs")
    asset_id = generate_asset_id("elevenlabs", "music")
    created_at = generate_timestamp()
    
    logger.info(f"Generating music: job_id={job_id}, prompt_length={len(prompt)}")
    
    try:
        # Call ElevenLabs API
        client = get_client()
        
        # Extract optional parameters
        optional_params = {}
        for key in ["temperature", "seed"]:
            if key in payload:
                optional_params[key] = payload[key]
        
        response = client.generate_music(
            prompt=prompt,
            duration=duration,
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
                "model": "music-generation",
                "params": {
                    "prompt": prompt,
                    "duration": duration,
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
                audio_url = f"data:audio/mpeg;base64,{response.get('audio', '')[:50]}..."
            
            completed_at = generate_timestamp()
            
            asset_link = AssetLink(
                url=audio_url or "pending",
                asset_id=asset_id,
                asset_type="music",
                provider="elevenlabs",
                created_at=completed_at
            )
            
            # Process links (download and store if enabled)
            links = process_asset_links([asset_link], project_name, "audio", completed_at)
            
            return {
                "job_id": job_id,
                "status": "completed",
                "provider": "elevenlabs",
                "model": "music-generation",
                "params": {
                    "prompt": prompt,
                    "duration": duration,
                    **optional_params
                },
                "created_at": created_at,
                "completed_at": completed_at,
                "links": links,
                "error": None
            }
    
    except Exception as e:
        logger.error(f"Error generating music: {e}", exc_info=True)
        raise
