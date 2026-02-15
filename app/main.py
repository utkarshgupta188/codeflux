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
from app.services.graph_service import GraphService
from app.services.context_builder import ContextBuilder
from app.services.impact_service import ImpactService
from app.models.repo import RepoScanRequest, ScanResult, RepoHealth
from app.models.graph_schemas import GraphResponse
from app.models.graph import Repository, GraphFile, Symbol, Edge
from app.models.version import RepoVersion
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


# ─── Code Search Endpoint ──────────────────────────────────────

class CodeSearchRequest(BaseModel):
    query: str
    file_type: str | None = None
    symbol_type: str | None = None
    case_sensitive: bool = False
    regex: bool = False
    limit: int = 100

class SearchResult(BaseModel):
    file: str
    line: int
    content: str
    symbol: str | None = None
    symbol_type: str | None = None

class CodeSearchResponse(BaseModel):
    results: list[SearchResult]
    total_matches: int
    truncated: bool

@app.post("/repo/{scan_id}/search", response_model=CodeSearchResponse)
async def search_code(
    scan_id: str,
    body: CodeSearchRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Full-text code search with filters.
    Searches through all files in the scanned repository.
    """
    from app.services.search_service import SearchService

    try:
        result = await SearchService.search(
            scan_id=scan_id,
            query=body.query,
            file_type=body.file_type,
            symbol_type=body.symbol_type,
            case_sensitive=body.case_sensitive,
            regex=body.regex,
            limit=body.limit,
            db=db,
        )
        return result
    except Exception as e:
        logger.error(f"Search failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ─── Documentation Generator ──────────────────────────────────

class GenerateDocsRequest(BaseModel):
    scope: str = "file"  # file | folder | repo
    path: str | None = None
    file: Optional[str] = None  # legacy support
    symbol: str | None = None
    format: str = "markdown"  # markdown | html | docstring
    max_files: int | None = None
    max_chars: int | None = None

    def model_post_init(self, __context):
        if self.path is None and self.file:
            self.path = self.file
        if self.path is not None and self.file is None:
            self.file = self.path

    @property
    def resolved_path(self) -> str | None:
        return self.path or self.file

class GenerateDocsResponse(BaseModel):
    documentation: str
    format: str
    generated_for: str
    included_files: list[str]
    truncated: bool
    stats: dict

@app.post("/repo/{scan_id}/generate-docs", response_model=GenerateDocsResponse)
async def generate_docs(
    scan_id: str,
    body: GenerateDocsRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    """
    AI-powered documentation generation for code.
    Analyzes code structure and generates comprehensive documentation.
    """
    from app.services.docs_service import DocsService

    try:
        if body.scope != "file":
            raise ValueError("Folder and repo scopes have been disabled. Please use file scope instead.")

        result = await DocsService.generate(
            scan_id=scan_id,
            scope=body.scope,
            path=body.resolved_path,
            symbol=body.symbol,
            format=body.format,
            max_files=body.max_files,
            max_chars=body.max_chars,
            db=db,
        )
        return result
    except Exception as e:
        logger.error(f"Documentation generation failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ─── Export & Reporting ──────────────────────────────────────

class ExportRequest(BaseModel):
    format: str = "json"  # json | markdown | html
    include_graph: bool = True
    include_health: bool = True
    include_hotspots: bool = True

from fastapi.responses import StreamingResponse
import json as json_lib

@app.post("/repo/{scan_id}/export")
async def export_report(
    scan_id: str,
    body: ExportRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Export repository analysis as JSON, Markdown, or HTML report.
    """
    from app.services.export_service import ExportService

    try:
        result = await ExportService.export(
            scan_id=scan_id,
            format=body.format,
            include_graph=body.include_graph,
            include_health=body.include_health,
            include_hotspots=body.include_hotspots,
            db=db,
        )

        # Determine content type and filename
        if body.format == "json":
            media_type = "application/json"
            filename = f"codeflux-report-{scan_id}.json"
        elif body.format == "markdown":
            media_type = "text/markdown"
            filename = f"codeflux-report-{scan_id}.md"
        else:  # html
            media_type = "text/html"
            filename = f"codeflux-report-{scan_id}.html"

        return StreamingResponse(
            iter([result]),
            media_type=media_type,
            headers={
                "Content-Disposition": f"attachment; filename={filename}"
            }
        )
    except Exception as e:
        logger.error(f"Export failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ─── Version History & Diff Viewer ──────────────────────────────

@app.get("/repo/{repo_id}/versions")
async def get_versions(repo_id: str, db: AsyncSession = Depends(get_db)):
    """Get all versions/scans for a repository."""
    from app.models.version import RepoVersion
    from app.models.graph import Repository

    # Find repo by scan_id or repo_id
    repo_result = await db.execute(
        select(Repository).where(Repository.scan_id == repo_id)
    )
    repo = repo_result.scalar_one_or_none()

    if not repo:
        raise HTTPException(status_code=404, detail="Repository not found")

    # Get all versions for this repo
    versions_result = await db.execute(
        select(RepoVersion)
        .where(RepoVersion.repo_id == repo.id)
        .order_by(RepoVersion.created_at.desc())
    )
    versions = versions_result.scalars().all()

    return [
        {
            "version_id": v.id,
            "scan_id": v.scan_id,
            "commit_hash": v.commit_hash,
            "created_at": v.created_at.isoformat() if v.created_at else None,
        }
        for v in versions
    ]


class DiffRequest(BaseModel):
    base_scan_id: str
    head_scan_id: str

class FileDiff(BaseModel):
    file: str
    status: str  # added | removed | modified
    symbols_added: int
    symbols_removed: int
    symbols_modified: int

class DiffResponse(BaseModel):
    base_scan_id: str
    head_scan_id: str
    files_changed: list[FileDiff]
    total_files_added: int
    total_files_removed: int
    total_files_modified: int
    symbols_changed: int

@app.post("/repo/diff", response_model=DiffResponse)
async def get_diff(body: DiffRequest, db: AsyncSession = Depends(get_db)):
    """
    Compare two scans and show what changed.
    """
    from app.services.diff_service import DiffService

    try:
        result = await DiffService.compare(
            base_scan_id=body.base_scan_id,
            head_scan_id=body.head_scan_id,
            db=db,
        )
        return result
    except Exception as e:
        logger.error(f"Diff comparison failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


