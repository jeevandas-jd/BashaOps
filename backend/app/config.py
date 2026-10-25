# backend/app/config.py
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    APP_ENV: str = "development"
    DATABASE_URL: str = "sqlite:///./bhashaops.db"
    
    # Gemma / Ollama Configuration
    GEMMA_BASE_URL: str = "http://localhost:11434"
    GEMMA_MODEL: str = "gemma4:e4b"  # Update this if your local model tag is different
    GEMMA_TIMEOUT: int = 30
    
    DEMO_MODE: bool = True

    # Pydantic V2 configuration for .env files
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

# Instantiate the settings object at the module level
settings = Settings()