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
from app.services.scanner import ScannerService
from app.services.graph_service import GraphService
from app.services.context_builder import ContextBuilder
from app.services.impact_service import ImpactService
from app.models.repo import RepoScanRequest, ScanResult, RepoHealth
from app.models.graph_schemas import GraphResponse
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

        background_tasks.add_task(
            log_request_background,
            prompt=request.prompt,
            provider=provider,
            model=model,
            latency_ms=latency_ms,
            fallback_used=fallback_used,
            tokens_used=result.get("tokens_used", 0) if 'result' in locals() else 0,
            estimated_cost=result.get("estimated_cost", 0.0) if 'result' in locals() else 0.0,
            routing_reason=result.get("routing_reason") if 'result' in locals() else None,
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

@app.get("/repo/{scan_id}/graph", response_model=GraphResponse)
async def get_repo_graph(scan_id: str, db: AsyncSession = Depends(get_db)):
    """Returns the structural code graph for a completed scan."""
    return await GraphService.get_graph(scan_id, db)


# ─── AI-Powered Repo Q&A ─────────────────────────────────

class RepoQuestion(BaseModel):
    question: str

class RepoAnswer(BaseModel):
    answer: str
    provider_used: str
    latency_ms: float

@app.post("/repo/{scan_id}/ask", response_model=RepoAnswer)
async def ask_repo(
    scan_id: str,
    body: RepoQuestion,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    """
    AI-powered repository Q&A.
    Builds structured context from graph + health data,
    injects it as system prompt, routes through Groq/OpenRouter.
    """
    import time
    start = time.time()

    # 1. Build context
    try:
        ctx = await ContextBuilder.build_context(scan_id, db)
    except Exception as e:
        logger.error(f"Context build failed for {scan_id}: {e}")
        raise HTTPException(status_code=404, detail="Scan data not found or graph not built yet.")

    if ctx.total_symbols == 0:
        raise HTTPException(status_code=404, detail="No graph data available. Scan or re-scan the repository first.")

    # 2. Build system prompt
    system_prompt = ContextBuilder.build_system_prompt(ctx)

    # 3. Route through gateway
    chat_request = ChatRequest(
        prompt=body.question,
        system_prompt=system_prompt,
        task_type="code_analysis",
    )

    try:
        result = await router_service.route_request(chat_request)
    except Exception as e:
        logger.error(f"AI routing failed: {e}")
        raise HTTPException(status_code=502, detail="All AI providers unavailable.")

    latency_ms = (time.time() - start) * 1000

    # 4. Log in background
    background_tasks.add_task(
        log_request_background,
        prompt=f"[repo-ask:{scan_id}] {body.question}",
        provider=result["provider"],
        model=result["model"],
        latency_ms=latency_ms,
        fallback_used=result.get("fallback_used", False),
        tokens_used=result.get("tokens_used", 0),
        estimated_cost=result.get("estimated_cost", 0.0),
        routing_reason=result.get("routing_reason"),
    )

    return RepoAnswer(
        answer=result["response"],
        provider_used=result["provider"],
        latency_ms=round(latency_ms, 2),
    )


# ─── Change Impact Simulation ──────────────────────────────

class SimulateChangeRequest(BaseModel):
    file: str | None = None
    symbol: str | None = None
    depth_limit: int = 5

class SimulateChangeResponse(BaseModel):
    affected_files: list[str]
    affected_symbols: list[dict]
    impact_score: float
    risk_increase: float
    max_depth: int
    total_affected: int
    circular_risk: bool

@app.post("/repo/{scan_id}/simulate-change", response_model=SimulateChangeResponse)
async def simulate_change(
    scan_id: str,
    body: SimulateChangeRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Deterministic change impact simulation.
    BFS traversal of the structural graph to compute blast radius.
    """
    if not body.file and not body.symbol:
        raise HTTPException(status_code=400, detail="Provide at least 'file' or 'symbol'.")

    depth = min(max(body.depth_limit, 1), 10)  # clamp 1-10

    result = await ImpactService.simulate(
        scan_id=scan_id,
        file=body.file,
        symbol=body.symbol,
        max_depth=depth,
        db=db,
    )

    return SimulateChangeResponse(
        affected_files=result.affected_files,
        affected_symbols=result.affected_symbols,
        impact_score=result.impact_score,
        risk_increase=result.risk_increase,
        max_depth=result.max_depth,
        total_affected=result.total_affected,
        circular_risk=result.circular_risk,
    )
