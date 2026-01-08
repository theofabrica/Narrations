"""
Structured logging configuration.
"""
import logging
import sys
from typing import Optional
from app.config.settings import settings


def setup_logger(name: Optional[str] = None) -> logging.Logger:
    """
    Setup a structured logger.
    
    Args:
        name: Logger name (defaults to root logger)
    
    Returns:
        Configured logger instance
    """
    logger = logging.getLogger(name or "mcp_narrations")
    
    # Avoid duplicate handlers
    if logger.handlers:
        return logger
    
    # Set log level from settings
    log_level = getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO)
    logger.setLevel(log_level)
    
    # Console handler with structured format
    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(log_level)
    
    # Format: timestamp | level | logger | message
    formatter = logging.Formatter(
        "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )
    handler.setFormatter(formatter)
    
    logger.addHandler(handler)
    logger.propagate = False
    
    return logger


# Default logger instance
logger = setup_logger()
