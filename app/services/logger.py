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
        fallback_used: bool,
        tokens_used: int = 0,
        estimated_cost: float = 0.0,
        routing_reason: str | None = None,
    ):
        """
        Persist request details to Postgres.
        Now includes token usage, cost, and routing decision metadata.
        """
        log_entry = RequestLog(
            prompt=prompt,
            provider_used=provider,
            model_used=model,
            latency_ms=latency_ms,
            fallback_used=fallback_used,
            tokens_used=tokens_used,
            estimated_cost=estimated_cost,
            routing_reason=routing_reason,
        )
        db.add(log_entry)
        await db.commit()
