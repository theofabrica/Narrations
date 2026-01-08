"""
Pipeline: Combine voice, sound effects, and music into a single audio stack.
"""
from typing import Dict, Any, List, Optional
from app.tools.elevenlabs import voice, music, soundfx
from app.tools.elevenlabs.client import get_client
from app.utils.ids import generate_job_id, generate_timestamp
from app.utils.errors import ValidationError
from app.utils.logging import logger
from app.mcp.schemas import AssetLink


def audio_stack(payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    Pipeline: Generate and combine voice, sound effects, and music.
    
    Expected payload:
        - voice: dict (optional) - Voice generation parameters
            - text: str (required if voice provided)
            - voice_id, model_id, stability, similarity_boost, style, use_speaker_boost
        - music: dict (optional) - Music generation parameters
            - prompt: str (required if music provided)
            - duration, temperature, seed
        - soundfx: dict (optional) - Sound effect generation parameters
            - prompt: str (required if soundfx provided)
            - duration, temperature, seed
        - At least one of voice, music, or soundfx must be provided
        - wait_for_completion: bool (optional) - Wait for all jobs to complete (default: True)
    
    Returns:
        Combined job status with links to all generated audio assets
    """
    # Validate payload - at least one audio type must be provided
    voice_params = payload.get("voice")
    music_params = payload.get("music")
    soundfx_params = payload.get("soundfx")
    
    if not voice_params and not music_params and not soundfx_params:
        raise ValidationError("At least one of voice, music, or soundfx must be provided")
    
    wait_for_completion = payload.get("wait_for_completion", True)
    
    # Generate pipeline job ID
    pipeline_job_id = generate_job_id("pipeline")
    created_at = generate_timestamp()
    
    logger.info(f"Starting audio_stack pipeline: pipeline_job_id={pipeline_job_id}")
    
    try:
        steps = []
        all_links = []
        all_job_ids = []
        errors = []
        
        # Step 1: Generate voice (if provided)
        if voice_params:
            if not voice_params.get("text"):
                raise ValidationError("voice.text is required when voice is provided")
            
            logger.info(f"Step 1: Generating voice for pipeline {pipeline_job_id}")
            voice_result = voice.generate_voice(voice_params)
            voice_job_id = voice_result.get("job_id")
            voice_status = voice_result.get("status")
            all_job_ids.append(voice_job_id)
            
            steps.append({
                "step": len(steps) + 1,
                "name": "voice_generation",
                "job_id": voice_job_id,
                "status": voice_status
            })
            
            if voice_status == "failed":
                errors.append({
                    "step": "voice_generation",
                    "error": voice_result.get("error")
                })
            elif voice_status == "completed":
                all_links.extend(voice_result.get("links", []))
            elif voice_status == "pending" and wait_for_completion:
                # Poll for voice completion
                logger.info(f"Polling for voice completion: job_id={voice_job_id}")
                elevenlabs_client = get_client()
                final_voice_status = elevenlabs_client.get_job_status(voice_job_id)
                
                # Simple polling loop (could be improved)
                max_polls = 60  # 5 minutes max at 5s intervals
                poll_count = 0
                while final_voice_status.get("status", "").lower() not in ["completed", "failed"] and poll_count < max_polls:
                    import time
                    time.sleep(5)
                    final_voice_status = elevenlabs_client.get_job_status(voice_job_id)
                    poll_count += 1
                
                voice_status = final_voice_status.get("status", "").lower()
                steps[-1]["status"] = voice_status
                
                if voice_status == "completed":
                    voice_url = final_voice_status.get("result_url") or final_voice_status.get("url")
                    if voice_url:
                        voice_asset = AssetLink(
                            url=voice_url,
                            asset_id=voice_result.get("asset_id", "unknown"),
                            asset_type="voice",
                            provider="elevenlabs",
                            created_at=generate_timestamp()
                        )
                        all_links.append(voice_asset.dict() if hasattr(voice_asset, 'dict') else voice_asset)
                elif voice_status == "failed":
                    errors.append({
                        "step": "voice_generation",
                        "error": final_voice_status.get("error")
                    })
        
        # Step 2: Generate music (if provided)
        if music_params:
            if not music_params.get("prompt"):
                raise ValidationError("music.prompt is required when music is provided")
            
            logger.info(f"Step 2: Generating music for pipeline {pipeline_job_id}")
            music_result = music.generate_music(music_params)
            music_job_id = music_result.get("job_id")
            music_status = music_result.get("status")
            all_job_ids.append(music_job_id)
            
            steps.append({
                "step": len(steps) + 1,
                "name": "music_generation",
                "job_id": music_job_id,
                "status": music_status
            })
            
            if music_status == "failed":
                errors.append({
                    "step": "music_generation",
                    "error": music_result.get("error")
                })
            elif music_status == "completed":
                all_links.extend(music_result.get("links", []))
            elif music_status == "pending" and wait_for_completion:
                # Poll for music completion
                logger.info(f"Polling for music completion: job_id={music_job_id}")
                elevenlabs_client = get_client()
                final_music_status = elevenlabs_client.get_job_status(music_job_id)
                
                max_polls = 60
                poll_count = 0
                while final_music_status.get("status", "").lower() not in ["completed", "failed"] and poll_count < max_polls:
                    import time
                    time.sleep(5)
                    final_music_status = elevenlabs_client.get_job_status(music_job_id)
                    poll_count += 1
                
                music_status = final_music_status.get("status", "").lower()
                steps[-1]["status"] = music_status
                
                if music_status == "completed":
                    music_url = final_music_status.get("result_url") or final_music_status.get("url")
                    if music_url:
                        music_asset = AssetLink(
                            url=music_url,
                            asset_id=music_result.get("asset_id", "unknown"),
                            asset_type="music",
                            provider="elevenlabs",
                            created_at=generate_timestamp()
                        )
                        all_links.append(music_asset.dict() if hasattr(music_asset, 'dict') else music_asset)
                elif music_status == "failed":
                    errors.append({
                        "step": "music_generation",
                        "error": final_music_status.get("error")
                    })
        
        # Step 3: Generate sound effects (if provided)
        if soundfx_params:
            if not soundfx_params.get("prompt"):
                raise ValidationError("soundfx.prompt is required when soundfx is provided")
            
            logger.info(f"Step 3: Generating sound effects for pipeline {pipeline_job_id}")
            soundfx_result = soundfx.generate_soundfx(soundfx_params)
            soundfx_job_id = soundfx_result.get("job_id")
            soundfx_status = soundfx_result.get("status")
            all_job_ids.append(soundfx_job_id)
            
            steps.append({
                "step": len(steps) + 1,
                "name": "soundfx_generation",
                "job_id": soundfx_job_id,
                "status": soundfx_status
            })
            
            if soundfx_status == "failed":
                errors.append({
                    "step": "soundfx_generation",
                    "error": soundfx_result.get("error")
                })
            elif soundfx_status == "completed":
                all_links.extend(soundfx_result.get("links", []))
            elif soundfx_status == "pending" and wait_for_completion:
                # Poll for soundfx completion
                logger.info(f"Polling for soundfx completion: job_id={soundfx_job_id}")
                elevenlabs_client = get_client()
                final_soundfx_status = elevenlabs_client.get_job_status(soundfx_job_id)
                
                max_polls = 60
                poll_count = 0
                while final_soundfx_status.get("status", "").lower() not in ["completed", "failed"] and poll_count < max_polls:
                    import time
                    time.sleep(5)
                    final_soundfx_status = elevenlabs_client.get_job_status(soundfx_job_id)
                    poll_count += 1
                
                soundfx_status = final_soundfx_status.get("status", "").lower()
                steps[-1]["status"] = soundfx_status
                
                if soundfx_status == "completed":
                    soundfx_url = final_soundfx_status.get("result_url") or final_soundfx_status.get("url")
                    if soundfx_url:
                        soundfx_asset = AssetLink(
                            url=soundfx_url,
                            asset_id=soundfx_result.get("asset_id", "unknown"),
                            asset_type="soundfx",
                            provider="elevenlabs",
                            created_at=generate_timestamp()
                        )
                        all_links.append(soundfx_asset.dict() if hasattr(soundfx_asset, 'dict') else soundfx_asset)
                elif soundfx_status == "failed":
                    errors.append({
                        "step": "soundfx_generation",
                        "error": final_soundfx_status.get("error")
                    })
        
        # Determine final status
        all_statuses = [step["status"] for step in steps]
        if "failed" in all_statuses:
            final_status = "failed"
            error = errors[0].get("error") if errors else {
                "code": "AUDIO_STACK_FAILED",
                "message": "One or more audio generation steps failed",
                "retryable": True
            }
        elif all(s == "completed" for s in all_statuses):
            final_status = "completed"
            error = None
        else:
            final_status = "pending"
            error = None
        
        completed_at = generate_timestamp() if final_status in ["completed", "failed"] else None
        
        return {
            "job_id": pipeline_job_id,
            "status": final_status,
            "provider": "pipeline",
            "model": "audio_stack",
            "params": {
                "voice": voice_params,
                "music": music_params,
                "soundfx": soundfx_params
            },
            "created_at": created_at,
            "completed_at": completed_at,
            "links": all_links,
            "error": error,
            "steps": steps
        }
    
    except Exception as e:
        logger.error(f"Error in audio_stack pipeline: {e}", exc_info=True)
        raise
