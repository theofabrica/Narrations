"""
Pipeline: Generate image then video from that image.
"""
from typing import Dict, Any, Optional
from app.tools.higgsfield import image, video
from app.tools.higgsfield.client import get_client
from app.utils.ids import generate_job_id, generate_timestamp
from app.utils.errors import ValidationError, ProviderError
from app.utils.logging import logger
from app.mcp.schemas import AssetLink


def image_to_video(payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    Pipeline: Generate image from prompt, then generate video from that image.
    
    Expected payload:
        - prompt: str (required) - Image generation prompt
        - image_params: dict (optional) - Parameters for image generation
            - model, width, height, steps, guidance_scale, seed
        - video_params: dict (optional) - Parameters for video generation
            - model, duration, fps, width, height, steps, seed
        - wait_for_completion: bool (optional) - Wait for both jobs to complete (default: True)
    
    Returns:
        Combined job status with links to both image and video
    """
    # Validate payload
    if not payload.get("prompt"):
        raise ValidationError("prompt is required")
    
    prompt = payload["prompt"]
    image_params = payload.get("image_params", {})
    video_params = payload.get("video_params", {})
    wait_for_completion = payload.get("wait_for_completion", True)
    
    # Generate pipeline job ID
    pipeline_job_id = generate_job_id("pipeline")
    created_at = generate_timestamp()
    
    logger.info(f"Starting image_to_video pipeline: pipeline_job_id={pipeline_job_id}, prompt_length={len(prompt)}")
    
    try:
        # Step 1: Generate image
        logger.info(f"Step 1: Generating image for pipeline {pipeline_job_id}")
        image_payload = {
            "prompt": prompt,
            "wait_for_completion": wait_for_completion,
            **image_params
        }
        
        image_result = image.generate_image(image_payload)
        image_job_id = image_result.get("job_id")
        image_status = image_result.get("status")
        
        # If image generation failed, return error
        if image_status == "failed":
            return {
                "job_id": pipeline_job_id,
                "status": "failed",
                "provider": "pipeline",
                "model": "image_to_video",
                "params": {
                    "prompt": prompt,
                    "image_params": image_params,
                    "video_params": video_params
                },
                "created_at": created_at,
                "completed_at": generate_timestamp(),
                "links": [],
                "error": image_result.get("error"),
                "steps": [
                    {
                        "step": 1,
                        "name": "image_generation",
                        "job_id": image_job_id,
                        "status": image_status,
                        "error": image_result.get("error")
                    }
                ]
            }
        
        # Wait for image if needed and not completed
        image_url = None
        if image_status == "pending" and wait_for_completion:
            logger.info(f"Polling for image completion: job_id={image_job_id}")
            higgsfield_client = get_client()
            final_image_status = higgsfield_client.poll_job(image_job_id)
            image_status = final_image_status.get("status", "pending").lower()
            
            if image_status == "completed":
                image_links = image_result.get("links", [])
                if image_links:
                    image_url = image_links[0].get("url") if isinstance(image_links[0], dict) else image_links[0].url
                else:
                    # Try to get from final status
                    image_url = final_image_status.get("result_url") or final_image_status.get("url")
            elif image_status in ["failed", "error"]:
                return {
                    "job_id": pipeline_job_id,
                    "status": "failed",
                    "provider": "pipeline",
                    "model": "image_to_video",
                    "params": {
                        "prompt": prompt,
                        "image_params": image_params,
                        "video_params": video_params
                    },
                    "created_at": created_at,
                    "completed_at": generate_timestamp(),
                    "links": [],
                    "error": {
                        "code": "IMAGE_GENERATION_FAILED",
                        "message": final_image_status.get("error", {}).get("message", "Image generation failed"),
                        "retryable": True
                    },
                    "steps": [
                        {
                            "step": 1,
                            "name": "image_generation",
                            "job_id": image_job_id,
                            "status": "failed",
                            "error": final_image_status.get("error")
                        }
                    ]
                }
        elif image_status == "completed":
            # Extract image URL from result
            image_links = image_result.get("links", [])
            if image_links:
                image_url = image_links[0].get("url") if isinstance(image_links[0], dict) else image_links[0].url
        
        # If we don't have image URL yet, return pending status
        if not image_url:
            return {
                "job_id": pipeline_job_id,
                "status": "pending",
                "provider": "pipeline",
                "model": "image_to_video",
                "params": {
                    "prompt": prompt,
                    "image_params": image_params,
                    "video_params": video_params
                },
                "created_at": created_at,
                "completed_at": None,
                "links": image_result.get("links", []),
                "error": None,
                "steps": [
                    {
                        "step": 1,
                        "name": "image_generation",
                        "job_id": image_job_id,
                        "status": image_status
                    }
                ]
            }
        
        # Step 2: Generate video from image
        logger.info(f"Step 2: Generating video from image for pipeline {pipeline_job_id}")
        video_payload = {
            "image_url": image_url,
            "wait_for_completion": wait_for_completion,
            **video_params
        }
        
        video_result = video.generate_video(video_payload)
        video_job_id = video_result.get("job_id")
        video_status = video_result.get("status")
        
        # Collect all links
        all_links = image_result.get("links", []) + video_result.get("links", [])
        
        # If video generation failed
        if video_status == "failed":
            return {
                "job_id": pipeline_job_id,
                "status": "failed",
                "provider": "pipeline",
                "model": "image_to_video",
                "params": {
                    "prompt": prompt,
                    "image_params": image_params,
                    "video_params": video_params
                },
                "created_at": created_at,
                "completed_at": generate_timestamp(),
                "links": all_links,
                "error": video_result.get("error"),
                "steps": [
                    {
                        "step": 1,
                        "name": "image_generation",
                        "job_id": image_job_id,
                        "status": "completed"
                    },
                    {
                        "step": 2,
                        "name": "video_generation",
                        "job_id": video_job_id,
                        "status": "failed",
                        "error": video_result.get("error")
                    }
                ]
            }
        
        # Wait for video if needed and not completed
        if video_status == "pending" and wait_for_completion:
            logger.info(f"Polling for video completion: job_id={video_job_id}")
            higgsfield_client = get_client()
            final_video_status = higgsfield_client.poll_job(video_job_id)
            video_status = final_video_status.get("status", "pending").lower()
            
            if video_status == "completed":
                video_links = video_result.get("links", [])
                if not video_links:
                    video_url = final_video_status.get("result_url") or final_video_status.get("url")
                    if video_url:
                        video_asset = AssetLink(
                            url=video_url,
                            asset_id=video_result.get("asset_id", "unknown"),
                            asset_type="video",
                            provider="higgsfield",
                            created_at=generate_timestamp()
                        )
                        all_links.append(video_asset.dict() if hasattr(video_asset, 'dict') else video_asset)
            elif video_status in ["failed", "error"]:
                return {
                    "job_id": pipeline_job_id,
                    "status": "failed",
                    "provider": "pipeline",
                    "model": "image_to_video",
                    "params": {
                        "prompt": prompt,
                        "image_params": image_params,
                        "video_params": video_params
                    },
                    "created_at": created_at,
                    "completed_at": generate_timestamp(),
                    "links": all_links,
                    "error": {
                        "code": "VIDEO_GENERATION_FAILED",
                        "message": final_video_status.get("error", {}).get("message", "Video generation failed"),
                        "retryable": True
                    },
                    "steps": [
                        {
                            "step": 1,
                            "name": "image_generation",
                            "job_id": image_job_id,
                            "status": "completed"
                        },
                        {
                            "step": 2,
                            "name": "video_generation",
                            "job_id": video_job_id,
                            "status": "failed",
                            "error": final_video_status.get("error")
                        }
                    ]
                }
        
        # Determine final status
        final_status = "completed" if (image_status == "completed" and video_status == "completed") else "pending"
        completed_at = generate_timestamp() if final_status == "completed" else None
        
        return {
            "job_id": pipeline_job_id,
            "status": final_status,
            "provider": "pipeline",
            "model": "image_to_video",
            "params": {
                "prompt": prompt,
                "image_params": image_params,
                "video_params": video_params
            },
            "created_at": created_at,
            "completed_at": completed_at,
            "links": all_links,
            "error": None,
            "steps": [
                {
                    "step": 1,
                    "name": "image_generation",
                    "job_id": image_job_id,
                    "status": image_status
                },
                {
                    "step": 2,
                    "name": "video_generation",
                    "job_id": video_job_id,
                    "status": video_status
                }
            ]
        }
    
    except Exception as e:
        logger.error(f"Error in image_to_video pipeline: {e}", exc_info=True)
        raise
