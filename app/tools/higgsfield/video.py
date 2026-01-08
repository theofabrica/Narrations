"""
Higgsfield video generation handler.
"""
from typing import Dict, Any
from app.tools.higgsfield.client import get_client
from app.utils.ids import generate_job_id, generate_asset_id, generate_timestamp
from app.utils.errors import ValidationError
from app.utils.logging import logger
from app.utils.media_storage import get_project_name, process_asset_links
from app.mcp.schemas import AssetLink


def generate_video(payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    Generate video from prompt or image using Higgsfield.
    
    Expected payload:
        - prompt: str (optional) - Video generation prompt (required if image_url not provided)
        - image_url: str (optional) - URL of source image (required if prompt not provided)
        - model: str (optional) - Model name
        - duration: float (optional) - Video duration in seconds
        - fps: int (optional) - Frames per second
        - width: int (optional) - Video width
        - height: int (optional) - Video height
        - steps: int (optional) - Number of steps
        - seed: int (optional) - Random seed
        - wait_for_completion: bool (optional) - Wait for job completion (default: False)
    
    Returns:
        Job status with asset links
    """
    # Validate payload
    if not payload.get("prompt") and not payload.get("image_url"):
        raise ValidationError("Either prompt or image_url is required")
    
    prompt = payload.get("prompt")
    image_url = payload.get("image_url")
    model = payload.get("model")
    wait_for_completion = payload.get("wait_for_completion", False)
    
    # Get project name from payload or trace
    trace = payload.get("_trace")
    project_name = get_project_name(payload, trace)
    
    # Generate IDs
    job_id = generate_job_id("higgsfield")
    asset_id = generate_asset_id("higgsfield", "video")
    created_at = generate_timestamp()
    
    logger.info(f"Generating video: job_id={job_id}, prompt={prompt is not None}, image_url={image_url is not None}")
    
    try:
        # Call Higgsfield API
        client = get_client()
        
        # Extract optional parameters
        optional_params = {}
        for key in ["duration", "fps", "width", "height", "steps", "seed"]:
            if key in payload:
                optional_params[key] = payload[key]
        
        response = client.generate_video(
            prompt=prompt,
            image_url=image_url,
            model=model,
            **optional_params
        )
        
        # Check if response contains job_id (async) or direct result
        if "job_id" in response:
            job_id = response["job_id"]
            status = "pending"
            completed_at = None
            links = []
            
            # Poll for completion if requested
            if wait_for_completion:
                logger.info(f"Polling for job completion: job_id={job_id}")
                final_status = client.poll_job(job_id)
                status = final_status.get("status", "pending").lower()
                
                if status == "completed":
                    completed_at = generate_timestamp()
                    video_url = final_status.get("result_url") or final_status.get("url")
                    if video_url:
                        asset_link = AssetLink(
                            url=video_url,
                            asset_id=asset_id,
                            asset_type="video",
                            provider="higgsfield",
                            created_at=completed_at
                        )
                        links = [asset_link.model_dump() if hasattr(asset_link, 'model_dump') else asset_link.dict()]
                        # Download and store locally
                        links = process_asset_links(links, project_name, "video", completed_at)
                elif status in ["failed", "error"]:
                    error_msg = final_status.get("error", {}).get("message", "Job failed")
                    return {
                        "job_id": job_id,
                        "status": "failed",
                        "provider": "higgsfield",
                        "model": model or "default",
                        "params": {
                            "prompt": prompt,
                            "image_url": image_url,
                            **optional_params
                        },
                        "created_at": created_at,
                        "completed_at": generate_timestamp(),
                        "links": [],
                        "error": {
                            "code": "JOB_FAILED",
                            "message": error_msg,
                            "retryable": True
                        }
                    }
            
            return {
                "job_id": job_id,
                "status": status,
                "provider": "higgsfield",
                "model": model or "default",
                "params": {
                    "prompt": prompt,
                    "image_url": image_url,
                    **optional_params
                },
                "created_at": created_at,
                "completed_at": completed_at,
                "links": links,
                "error": None
            }
        else:
            # Synchronous response with video
            video_url = response.get("video_url") or response.get("url") or response.get("result_url")
            if not video_url and "video" in response:
                video_url = f"data:video/mp4;base64,{response.get('video', '')[:50]}..."
            
            completed_at = generate_timestamp()
            
            asset_link = AssetLink(
                url=video_url or "pending",
                asset_id=asset_id,
                asset_type="video",
                provider="higgsfield",
                created_at=completed_at
            )
            
            # Process links (download and store if enabled)
            links = process_asset_links([asset_link], project_name, "video", completed_at)
            
            return {
                "job_id": job_id,
                "status": "completed",
                "provider": "higgsfield",
                "model": model or "default",
                "params": {
                    "prompt": prompt,
                    "image_url": image_url,
                    **optional_params
                },
                "created_at": created_at,
                "completed_at": completed_at,
                "links": links,
                "error": None
            }
    
    except Exception as e:
        logger.error(f"Error generating video: {e}", exc_info=True)
        raise
