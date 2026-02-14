# CodeFlux — AI Gateway & Code Intelligence Engine

A production-grade AI Gateway with intelligent routing, real-time observability, and AST-based code analysis — built with FastAPI + React.

## Features

### 🤖 AI Routing Gateway
- **Multi-Provider**: Groq (primary) + OpenRouter (fallback) with automatic failover
- **Smart Routing**: Route by provider preference, model override, or auto-select
- **Async**: Built on `asyncio` + `SQLAlchemy[async]` for high concurrency

### 📊 Observability
- Real-time metrics: Avg/P95 latency, request counts, fallback rate, provider split
- Time-range filtering (1h / 24h / 7d)
- Structured logging to PostgreSQL (prod) or SQLite (dev)

### 🔍 Repository Scanner
- **Local & GitHub**: Scan local directories or clone public GitHub repos (`git clone --depth 1`)
- **Static Analysis**: File count, dependency parsing (`package.json`, `requirements.txt`), symbol extraction
- **Complexity Scoring**: LOC + nesting depth + risk pattern detection (`eval`, `exec`)
- **Health Report**: Risk score (0-100), circular dependencies, top hotspots

### 🧠 AST Structural Graph Engine (Python)
- Full `ast.NodeVisitor` parsing — extracts modules, classes, functions, methods, imports, calls
- **Graph Relationships**: `defines`, `calls`, `imports` edges with best-effort name resolution
- **Circular Dependency Detection**: DFS with 3-color marking on import and call graphs
- **Persisted to DB**: 4 tables (`repositories`, `graph_files`, `symbols`, `edges`)
- **API**: `GET /repo/{id}/graph` returns full node/edge/cycle JSON

### 🎨 React Dashboard
- **3-page SPA**: Repo Scanner, Metrics Dashboard, AI Gateway Playground
- Tabbed navigation, mobile-responsive, dark theme
- Real-time backend health check (auto-polls every 30s)
- Localhost detection — "Local Path" option hidden in production

## Quick Start

```bash
git clone https://github.com/utkarshgupta188/codeflux.git
cd codeflux

# Configure
cp .env.example .env   # Add your GROQ_API_KEY and OPENROUTER_API_KEY

# Backend
pip install -r requirements.txt
uvicorn app.main:app --reload

# Frontend (separate terminal)
cd dashboard
npm install && npm run dev
```

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/chat` | Send AI prompt (auto-routed) |
| `GET` | `/metrics/summary?range=last_24h` | Gateway metrics |
| `POST` | `/repo/scan` | Start repository scan |
| `GET` | `/repo/{id}/status` | Poll scan progress |
| `GET` | `/repo/{id}/health` | Health report |
| `GET` | `/repo/{id}/graph` | Structural code graph |
| `GET` | `/health` | Backend health check |

## Project Structure

```
app/
├── adapters/          # LLM providers (Groq, OpenRouter)
├── models/            # Pydantic + SQLAlchemy schemas
│   ├── graph.py       # Graph ORM (Repository, Symbol, Edge)
│   └── repo.py        # Scanner schemas
├── services/
│   ├── ast_visitor.py  # AST NodeVisitor for Python
│   ├── graph_service.py # Graph builder + cycle detection
│   ├── scanner.py      # File walker + GitHub cloner
│   ├── router.py       # AI request routing
│   └── metrics.py      # Observability aggregation
└── main.py            # FastAPI app + routes

dashboard/             # React + Vite + TailwindCSS
├── src/components/    # RepoScanner, HealthDashboard, MetricsDashboard, GatewayPlayground
└── src/services/      # Unified API client
```

## Docker

```bash
docker-compose up --build
```
