import logging
import asyncio
import sys
from contextlib import asynccontextmanager
from typing import Optional

from fastapi import FastAPI, Depends, BackgroundTasks, HTTPException
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.utils.db import get_db, engine, Base
from app.models.api import ChatRequest, ChatResponse
from app.models.metrics import MetricsSummary, TimeRange
from app.services.router import RoutingService
from app.services.logger import LoggingService
from app.services.metrics import MetricsService
from app.services.scanner import ScannerService
from app.services.readme_service import ReadmeService
from app.models.repo import RepoScanRequest, ScanResult, RepoHealth, ReadmeResponse
from pydantic import BaseModel

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

from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:5174", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

async def log_request_background(
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
    Independent wrapper to manually manage DB session for background task.
    We don't reuse the dependency session because it might incur race conditions or close early.
    """
    from app.utils.db import AsyncSessionLocal
    async with AsyncSessionLocal() as session:
        try:
            await LoggingService.log_request(
                session, prompt, provider, model, latency_ms, fallback_used,
                tokens_used=tokens_used,
                estimated_cost=estimated_cost,
                routing_reason=routing_reason,
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

        # Define result if not already defined (in case of exception)
        if 'result' not in locals():
            result = {}

        background_tasks.add_task(
            log_request_background,
            prompt=request.prompt,
            provider=provider,
            model=model,
            latency_ms=latency_ms,
            fallback_used=fallback_used,
            tokens_used=result.get("tokens_used", 0),
            estimated_cost=result.get("estimated_cost", 0.0),
            routing_reason=result.get("routing_reason"),
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


@app.get("/metrics/cost")
async def get_cost_metrics():
    """
    Real-time cost metrics from in-memory tracker.
    Returns daily cost per provider, scoring state, and policy config.
    """
    from app.services.router import cost_tracker
    from app.config import get_settings
    s = get_settings()

    snapshot = cost_tracker.get_snapshot()

    return {
        "date": str(cost_tracker._date),
        "providers": snapshot,
        "policy": {
            "daily_limits": {
                "groq": s.DAILY_COST_LIMIT_GROQ,
                "openrouter": s.DAILY_COST_LIMIT_OPENROUTER,
            },
            "latency_spike_ms": s.LATENCY_SPIKE_MS,
            "weights": {
                "latency": s.WEIGHT_LATENCY,
                "fallback": s.WEIGHT_FALLBACK,
                "cost": s.WEIGHT_COST,
            },
            "cost_per_1k_tokens": {
                "groq": s.COST_PER_1K_GROQ,
                "openrouter": s.COST_PER_1K_OPENROUTER,
            },
        },
    }

@app.get("/health")
async def health_check():
    return {"status": "ok"}

# Repository Scanner Routes
@app.post("/repo/scan", response_model=ScanResult)
async def scan_repo(request: RepoScanRequest):
    return await ScannerService.start_scan(request)

@app.get("/repo/{scan_id}/status", response_model=ScanResult)
async def get_scan_status(scan_id: str):
    try:
        return ScannerService.get_status(scan_id)
    except KeyError:
        raise HTTPException(status_code=404, detail="Scan not found")

@app.get("/repo/{scan_id}/health", response_model=RepoHealth)
async def get_repo_health(scan_id: str):
    try:
        return ScannerService.get_health(scan_id)
    except KeyError:
        raise HTTPException(status_code=404, detail="Health data not found")

@app.post("/repo/{scan_id}/generate-readme", response_model=ReadmeResponse)
async def generate_readme(scan_id: str):
    if scan_id not in ScannerService.SCANS:
        raise HTTPException(status_code=404, detail="Repository scan not found. Scan it first.")
    
    try:
        return await ReadmeService.generate(scan_id)
    except Exception as e:
        logger.error(f"Error generating README: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ─── Agent Endpoint ──────────────────────────────────────────

class AgentRequest(BaseModel):
    prompt: str
    repo_id: str

@app.post("/agent/run")
async def run_agent(req: AgentRequest):
    """Run the autonomous coding agent."""
    from app.services.agent.agent_service import AgentService
    try:
        result = await AgentService.run(req.prompt, req.repo_id)
        return result
    except Exception as e:
        logger.error(f"Agent run failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


