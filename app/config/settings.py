"""
Configuration settings using Pydantic Settings.
Loads from environment variables and .env file.
"""
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional
import os


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True
    )
    
    # App environment
    APP_ENV: str = "development"
    LOG_LEVEL: str = "INFO"
    
    # Higgsfield API
    HIGGSFIELD_API_KEY: Optional[str] = None  # legacy single-key bearer
    HIGGSFIELD_API_KEY_ID: Optional[str] = None  # for "Key id:secret" auth
    HIGGSFIELD_API_KEY_SECRET: Optional[str] = None
    HIGGSFIELD_BASE_URL: str = "https://platform.higgsfield.ai"
    HIGGSFIELD_TIMEOUT: int = 300  # seconds
    HIGGSFIELD_RETRIES: int = 3
    HIGGSFIELD_POLLING_INTERVAL: int = 5  # seconds
    
    # ElevenLabs API
    ELEVENLABS_API_KEY: Optional[str] = None
    ELEVENLABS_BASE_URL: str = "https://api.elevenlabs.io/v1"
    ELEVENLABS_TIMEOUT: int = 300  # seconds
    ELEVENLABS_RETRIES: int = 3
    ELEVENLABS_POLLING_INTERVAL: int = 5  # seconds
    
    # Server settings
    HOST: str = "0.0.0.0"
    PORT: int = 3333
    
    # Storage settings
    STORAGE_PATH: Optional[str] = None  # Default: Media/ at project root
    STORAGE_DOWNLOAD_ENABLED: bool = True  # Automatically download and store media files
    STORAGE_FTP_ENABLED: bool = False  # Enable SFTP upload for media files
    DATA_PATH: Optional[str] = None  # Default: data/ at project root

    # FTP/SFTP settings
    FTP_HOST: Optional[str] = None
    FTP_PORT: int = 22
    FTP_USER: Optional[str] = None
    FTP_PASSWORD: Optional[str] = None
    FTP_BASE_DIR: str = "/"  # Remote base directory
    FTP_PUBLIC_BASE_URL: Optional[str] = None  # Public base URL to access uploaded files

    # OpenAI (for local agent scripts)
    OPENAI_API_KEY: Optional[str] = None  # Ignored by the server, but allowed in env


# Global settings instance
settings = Settings()
