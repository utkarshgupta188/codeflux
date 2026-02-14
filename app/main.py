import logging
import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI, Depends, BackgroundTasks, HTTPException
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.utils.db import get_db, engine, Base
from app.models.api import ChatRequest, ChatResponse
from app.models.metrics import MetricsSummary, TimeRange
from app.services.router import RoutingService
from app.services.logger import LoggingService
from app.services.metrics import MetricsService

# Setup Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("ai_gateway")

# Initialize Services
router_service = RoutingService()

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Ensure DB tables exist
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    # Shutdown
    await engine.dispose()

app = FastAPI(
    title="AI Routing Gateway",
    description="Control plane for routing AI requests with fallback strategies.",
    version="1.0.0",
    lifespan=lifespan
)

async def log_request_background(
    prompt: str,
    provider: str,
    model: str,
    latency_ms: float,
    fallback_used: bool,
):
    """
    Independent wrapper to manually manage DB session for background task.
    We don't reuse the dependency session because it might incur race conditions or close early.
    """
    from app.utils.db import AsyncSessionLocal
    async with AsyncSessionLocal() as session:
        try:
            await LoggingService.log_request(
                session, prompt, provider, model, latency_ms, fallback_used
            )
        except Exception as e:
            logger.error(f"Failed to log request: {e}")

@app.post("/chat", response_model=ChatResponse)
async def chat_endpoint(
    request: ChatRequest,
    background_tasks: BackgroundTasks
):
    import time
    start_time = time.time()
    
    # Defaults in case of failure
    provider = "unknown"
    model = "unknown"
    fallback_used = False
    
    try:
        # Route Request
        result = await router_service.route_request(request)
        
        provider = result["provider"]
        model = result["model"]
        fallback_used = result["fallback_used"]
        latency_ms = result["latency_ms"]
        
        return ChatResponse(
            response=result["response"],
            model_used=model,
            provider_used=provider,
            latency_ms=round(latency_ms, 2)
        )
        
    except Exception as e:
        logger.error(f"Request failed: {str(e)}")
        # Log failure
        latency_ms = (time.time() - start_time) * 1000
        
        # We must return a Response object to attach background tasks when an error occurs
        # Raising HTTPException skips background task execution from this scope
        return JSONResponse(
            status_code=502, 
            content={"detail": "All AI providers unavailable"},
            background=background_tasks
        )
        
    finally:
        # Schedule Logging (Non-blocking) - Executes for both success and failure
        # We need to calculate latency if not already set by success path
        if 'latency_ms' not in locals():
             latency_ms = (time.time() - start_time) * 1000

        background_tasks.add_task(
            log_request_background,
            prompt=request.prompt,
            provider=provider,
            model=model,
            latency_ms=latency_ms,
            fallback_used=fallback_used
        )

@app.get("/metrics/summary", response_model=MetricsSummary)
async def get_metrics(
    range: TimeRange = TimeRange.last_24h,
    db: AsyncSession = Depends(get_db)
):
    """
    Get aggregated system metrics for a specific time range.
    """
    return await MetricsService.get_summary(db, range)

@app.get("/health")
async def health_check():
    return {"status": "ok"}
