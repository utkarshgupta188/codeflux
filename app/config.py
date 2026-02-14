from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache

class Settings(BaseSettings):
    GROQ_API_KEY: str
    OPENROUTER_API_KEY: str
    DATABASE_URL: str
    
    DEFAULT_MODEL_GROQ: str = "llama-3.3-70b-versatile"
    DEFAULT_MODEL_OPENROUTER: str = "openai/gpt-3.5-turbo"
    
    LOG_LEVEL: str = "INFO"

    # ─── Cost-Aware Routing Policy ──────────────────────
    # Daily cost limit per provider (USD). Exceeded → deprioritize.
    DAILY_COST_LIMIT_GROQ: float = 5.0
    DAILY_COST_LIMIT_OPENROUTER: float = 10.0

    # Latency spike threshold (ms). Above → deprioritize.
    LATENCY_SPIKE_MS: float = 5000.0

    # Scoring weights (lower score = preferred provider)
    WEIGHT_LATENCY: float = 0.3
    WEIGHT_FALLBACK: float = 0.3
    WEIGHT_COST: float = 0.4

    # Cost per 1K tokens (USD) — estimates for scoring
    COST_PER_1K_GROQ: float = 0.0003
    COST_PER_1K_OPENROUTER: float = 0.002

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

@lru_cache
def get_settings():
    return Settings()
