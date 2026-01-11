"""
Higgsfield image generation handler.
"""
from typing import Dict, Any
from app.tools.higgsfield.client import get_client
from app.utils.ids import generate_job_id, generate_asset_id, generate_timestamp
from app.utils.errors import ValidationError
from app.utils.logging import logger
from app.utils.media_storage import get_project_name, process_asset_links
from app.mcp.schemas import AssetLink


def generate_image(payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    Generate image from prompt using Higgsfield.
    
    Expected payload:
        - prompt: str (required) - Image generation prompt
        - model: str (optional) - Model name
        - width: int (optional) - Image width
        - height: int (optional) - Image height
        - steps: int (optional) - Number of steps
        - guidance_scale: float (optional) - Guidance scale
        - seed: int (optional) - Random seed
        - wait_for_completion: bool (optional) - Wait for job completion (default: False)
    
    Returns:
        Job status with asset links
    """
    # Validate payload
    if not payload.get("prompt"):
        raise ValidationError("prompt is required")
    
    prompt = payload["prompt"]
    model = payload.get("model")
    wait_for_completion = payload.get("wait_for_completion", False)
    
    # Get project name from payload or trace
    trace = payload.get("_trace")
    project_name = get_project_name(payload, trace)
    
    # Generate IDs
    job_id = generate_job_id("higgsfield")
    asset_id = generate_asset_id("higgsfield", "image")
    created_at = generate_timestamp()
    
    logger.info(f"Generating image: job_id={job_id}, prompt_length={len(prompt)}")
    
    try:
        # Call Higgsfield API
        client = get_client()
        
        # Extract optional parameters
        optional_params = {}
        for key in [
            "width",
            "height",
            "steps",
            "guidance_scale",
            "seed",
            "aspect_ratio",
            "num_images",
            "output_format",
            "input_images"
        ]:
            if key in payload:
                optional_params[key] = payload[key]
        
        response = client.generate_image(
            prompt=prompt,
            model=model,
            **optional_params
        )
        provider_debug = response.pop("_provider_debug", None)
        
        # Check if response contains job_id (async) or direct result
        if "job_id" in response:
            job_id = response["job_id"]
            status = "pending"
            completed_at = None
            links = []
            status_url = response.get("status_url")
            
            # Poll for completion if requested
            if wait_for_completion:
                logger.info(f"Polling for job completion: job_id={job_id}")
                if model and model.replace("_", "-").lower() in {"nano-banana", "nano-banana-pro"}:
                    final_status = client.poll_request(job_id)
                else:
                    final_status = client.poll_job(job_id)
                status = final_status.get("status", "pending").lower()
                
                if status == "completed":
                    completed_at = generate_timestamp()
                    image_url = final_status.get("result_url") or final_status.get("url")
                    if image_url:
                        asset_link = AssetLink(
                            url=image_url,
                            asset_id=asset_id,
                            asset_type="image",
                            provider="higgsfield",
                            created_at=completed_at
                        )
                        links = [asset_link.model_dump() if hasattr(asset_link, 'model_dump') else asset_link.dict()]
                        # Download and store locally
                        links = process_asset_links(links, project_name, "image", completed_at)
                elif status in ["failed", "error"]:
                    error_msg = final_status.get("error", {}).get("message", "Job failed")
                    return {
                        "job_id": job_id,
                        "status": "failed",
                        "provider": "higgsfield",
                        "model": model or "default",
                        "params": {
                            "prompt": prompt,
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
            
            result = {
                "job_id": job_id,
                "status": status,
                "provider": "higgsfield",
                "model": model or "default",
                "params": {
                    "prompt": prompt,
                    **optional_params
                },
                "created_at": created_at,
                "completed_at": completed_at,
                "links": links,
                "error": None
            }
            if provider_debug:
                result["provider_debug"] = provider_debug
            if status_url:
                result["status_url"] = status_url
            return result
        else:
            # Synchronous response with image
            image_url = response.get("image_url") or response.get("url") or response.get("result_url")
            if not image_url and "image" in response:
                image_url = f"data:image/png;base64,{response.get('image', '')[:50]}..."

            if not image_url:
                result = {
                    "job_id": response.get("job_id", job_id),
                    "status": "pending",
                    "provider": "higgsfield",
                    "model": model or "default",
                    "params": {
                        "prompt": prompt,
                        **optional_params
                    },
                    "created_at": created_at,
                    "completed_at": None,
                    "links": [],
                    "error": None
                }
                if provider_debug:
                    result["provider_debug"] = provider_debug
                return result
            
            completed_at = generate_timestamp()
            
            asset_link = AssetLink(
                url=image_url or "pending",
                asset_id=asset_id,
                asset_type="image",
                provider="higgsfield",
                created_at=completed_at
            )
            
            # Process links (download and store if enabled)
            links = process_asset_links([asset_link], project_name, "image", completed_at)
            
            result = {
                "job_id": job_id,
                "status": "completed",
                "provider": "higgsfield",
                "model": model or "default",
                "params": {
                    "prompt": prompt,
                    **optional_params
                },
                "created_at": created_at,
                "completed_at": completed_at,
                "links": links,
                "error": None
            }
            if provider_debug:
                result["provider_debug"] = provider_debug
            return result
    
    except Exception as e:
        logger.error(f"Error generating image: {e}", exc_info=True)
        raise
