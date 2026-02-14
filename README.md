# CodeFlux — AI Gateway & Code Intelligence Engine

A production-grade AI Gateway with intelligent routing, real-time observability, and AST-based code analysis — built with FastAPI + React.

## 🌟 Key Features

### 🤖 AI Routing Gateway
- **Multi-Provider Support**: Groq (primary) + OpenRouter (fallback) with automatic failover.
- **Cost-Aware Intelligent Routing**: Routes based on a scoring formula: `Latency × W + Cost × W + Failures × W`.
- **Policy Enforcement**: Automatically deprioritizes providers that exceed daily cost limits or have latency spikes.
- **Async & Resilient**: Built on `asyncio` for high concurrency.

### 💰 Real-Time Cost Dashboard
- **Live Budget Tracking**: Monitor daily provider spend against configured limits.
- **Routing Insights**: View real-time provider scores, average latency, and fallback rates.
- **Policy Config**: Visualize active routing policies (latency penalties, cost weights).

### 🔍 Repository Scanner & Graph Engine
- **Deep Scanning**: Parses Python/JS/TS codebases to build a structural dependency graph.
- **AST Parsing**: Extracts `classes`, `functions`, `imports`, and `calls` to map relationships.
- **Health Analysis**: Detects circular dependencies and calculates complexity scores.
- **Interactive Visualization**: 2D/3D force-directed graph of your codebase.

### 💬 AI-Powered Repo Q&A
- **Context-Aware Chat**: Ask questions about your codebase (e.g., "How does auth work?").
- **RAG Pipeline**: Retrieves relevant code context from the graph before answering.

### 💥 Change Impact Simulator
- **Predictive Analysis**: Simulate changes to a file or symbol to see what breaks.
- **Impact Scoring**: Calculates risk based on dependency depth and breadth.
- **Visual Feedback**: highlights affected files and specific symbols in the dependency chain.

---

## 🚀 Quick Start

```bash
git clone https://github.com/utkarshgupta188/codeflux.git
cd codeflux

# 1. Configure
cp .env.example .env   
# Add your GROQ_API_KEY and OPENROUTER_API_KEY
# Optional: Adjust COST_PER_1K_*, DAILY_COST_LIMIT_*, etc.

# 2. Backend
pip install -r requirements.txt
uvicorn app.main:app --reload

# 3. Frontend (separate terminal)
cd dashboard
npm install && npm run dev
```

## 📚 API Endpoints

### AI Gateway
| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/chat` | Send AI prompt (auto-routed or manual override) |
| `GET` | `/metrics/summary` | Aggregate metrics (latency, vol, fallback rate) |
| `GET` | `/metrics/cost` | Real-time cost tracking & policy status |

### Repository Intelligence
| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/repo/scan` | detailed AST scan of local/remote repo |
| `GET` | `/repo/{id}/graph` | Full node/edge dependency graph |
| `POST` | `/repo/{id}/ask` | RAG-based Q&A about the codebase |
| `POST` | `/repo/{id}/simulate-change` | BFS-based change impact analysis |
| `GET` | `/repo/{id}/health` | Health report & circular deps |

## 🏗 Project Structure

```
app/
├── adapters/          # AI Providers (Groq, OpenRouter)
├── models/            # Pydantic Schemas & SQLAlchemy ORM
├── services/
│   ├── ast_visitor.py  # AST Parsing (Python)
│   ├── graph_service.py # Graph logic & cycle detection
│   ├── impact_service.py # BFS Impact Simulation
│   ├── router.py       # Cost-aware routing logic
│   └── logger.py       # Async logging
└── main.py            # FastAPI Routes

dashboard/             # React + Vite + TailwindCSS
├── src/components/    
│   ├── CostDashboard.tsx    # Live budget & policy view
│   ├── ImpactSimulator.tsx  # Change impact UI
│   ├── RepoChat.tsx         # AI Q&A Interface
│   ├── GraphViewer.tsx      # Interactive Graph Viz
│   └── GatewayPlayground.tsx # AI Routing Tester
```

## 🐳 Docker

```bash
docker-compose up --build
```
