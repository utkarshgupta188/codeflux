from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache

class Settings(BaseSettings):
    GROQ_API_KEY: str
    OPENROUTER_API_KEY: str
    DATABASE_URL: str
    
    DEFAULT_MODEL_GROQ: str = "llama-3.3-70b-versatile"
    DEFAULT_MODEL_OPENROUTER: str = "openai/gpt-3.5-turbo"
    
    LOG_LEVEL: str = "INFO"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

@lru_cache
def get_settings():
    return Settings()
