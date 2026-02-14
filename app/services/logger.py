from sqlalchemy.ext.asyncio import AsyncSession
from app.models.db import RequestLog

class LoggingService:
    @staticmethod
    async def log_request(
        db: AsyncSession,
        prompt: str,
        provider: str,
        model: str,
        latency_ms: float,
        fallback_used: bool
    ):
        """
        Persist request details to Postgres.
        """
        log_entry = RequestLog(
            prompt=prompt,
            provider_used=provider,
            model_used=model,
            latency_ms=latency_ms,
            fallback_used=fallback_used
        )
        db.add(log_entry)
        await db.commit()
