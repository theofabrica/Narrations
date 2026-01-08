"""
Action registry for dispatching MCP actions to handlers.
"""
from typing import Dict, Callable, Any, Optional
from app.utils.errors import ActionNotFoundError, ValidationError
from app.utils.logging import logger

# Import handlers (lazy import to avoid circular dependencies)
def _import_handlers():
    """Import handlers when needed."""
    from app.tools.elevenlabs import voice, music, soundfx
    from app.tools.higgsfield import image, video
    from app.tools.elevenlabs.client import get_client as get_elevenlabs_client
    from app.tools.higgsfield.client import get_client as get_higgsfield_client
    from app.pipelines.image_to_video import image_to_video
    from app.pipelines.audio_stack import audio_stack
    return {
        "elevenlabs": {
            "voice": voice.generate_voice,
            "music": music.generate_music,
            "soundfx": soundfx.generate_soundfx,
            "client": get_elevenlabs_client
        },
        "higgsfield": {
            "image": image.generate_image,
            "video": video.generate_video,
            "client": get_higgsfield_client
        },
        "pipelines": {
            "image_to_video": image_to_video,
            "audio_stack": audio_stack
        }
    }


# Registry mapping action names to handler functions
_action_registry: Dict[str, Callable[[Dict[str, Any]], Dict[str, Any]]] = {}


def register_action(action: str) -> Callable:
    """
    Decorator to register an action handler.
    
    Usage:
        @register_action("ping")
        def handle_ping(payload: Dict[str, Any]) -> Dict[str, Any]:
            return {"message": "pong"}
    """
    def decorator(func: Callable[[Dict[str, Any]], Dict[str, Any]]) -> Callable:
        if action in _action_registry:
            logger.warning(f"Action '{action}' is being overwritten")
        _action_registry[action] = func
        logger.debug(f"Registered action: {action}")
        return func
    return decorator


def get_action_handler(action: str) -> Optional[Callable[[Dict[str, Any]], Dict[str, Any]]]:
    """
    Get handler for an action.
    
    Args:
        action: Action name
    
    Returns:
        Handler function or None if not found
    """
    return _action_registry.get(action)


def list_actions() -> list[str]:
    """
    List all registered actions.
    
    Returns:
        List of action names
    """
    return sorted(_action_registry.keys())


def dispatch_action(action: str, payload: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Dispatch an action to its handler.
    
    Args:
        action: Action name
        payload: Action payload
    
    Returns:
        Response data from handler
    
    Raises:
        ActionNotFoundError: If action is not registered
    """
    handler = get_action_handler(action)
    if not handler:
        raise ActionNotFoundError(action)
    
    logger.info(f"Dispatching action: {action}")
    return handler(payload or {})


# Register built-in actions
@register_action("ping")
def handle_ping(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Handle ping action."""
    return {
        "message": "pong",
        "timestamp": payload.get("timestamp")
    }


@register_action("list_tools")
def handle_list_tools(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Handle list_tools action."""
    return {
        "actions": list_actions(),
        "count": len(_action_registry)
    }


# Register ElevenLabs actions
@register_action("elevenlabs_voice")
def handle_elevenlabs_voice(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Handle ElevenLabs voice generation."""
    handlers = _import_handlers()
    return handlers["elevenlabs"]["voice"](payload)


@register_action("elevenlabs_music")
def handle_elevenlabs_music(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Handle ElevenLabs music generation."""
    handlers = _import_handlers()
    return handlers["elevenlabs"]["music"](payload)


@register_action("elevenlabs_soundfx")
def handle_elevenlabs_soundfx(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Handle ElevenLabs sound effect generation."""
    handlers = _import_handlers()
    return handlers["elevenlabs"]["soundfx"](payload)


# Register Higgsfield actions
@register_action("higgsfield_image")
def handle_higgsfield_image(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Handle Higgsfield image generation."""
    handlers = _import_handlers()
    return handlers["higgsfield"]["image"](payload)


@register_action("higgsfield_video")
def handle_higgsfield_video(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Handle Higgsfield video generation."""
    handlers = _import_handlers()
    return handlers["higgsfield"]["video"](payload)


# Register job status check actions
@register_action("check_job_status")
def handle_check_job_status(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Check status of a job from any provider."""
    if not payload.get("job_id"):
        raise ValidationError("job_id is required")
    if not payload.get("provider"):
        raise ValidationError("provider is required")
    
    job_id = payload["job_id"]
    provider = payload["provider"].lower()
    
    handlers = _import_handlers()
    
    if provider == "elevenlabs":
        client = handlers["elevenlabs"]["client"]()
        status = client.get_job_status(job_id)
    elif provider == "higgsfield":
        client = handlers["higgsfield"]["client"]()
        status = client.get_job_status(job_id)
    else:
        raise ValidationError(f"Unknown provider: {provider}")
    
    return status


# Register pipeline actions
@register_action("pipeline_image_to_video")
def handle_pipeline_image_to_video(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Handle image_to_video pipeline."""
    handlers = _import_handlers()
    return handlers["pipelines"]["image_to_video"](payload)


@register_action("pipeline_audio_stack")
def handle_pipeline_audio_stack(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Handle audio_stack pipeline."""
    handlers = _import_handlers()
    return handlers["pipelines"]["audio_stack"](payload)
