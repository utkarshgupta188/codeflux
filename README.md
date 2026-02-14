# CodeFlux — AI Gateway & Code Intelligence Engine

A production-grade AI Gateway with intelligent routing, real-time observability, and AST-based code analysis — built with FastAPI + React.

## 🌟 Key Features

### 🤖 AI Routing Gateway
- **Multi-Provider Support**: Groq (primary) + OpenRouter (fallback) with automatic failover.
- **Cost-Aware Intelligent Routing**: Routes based on a scoring formula: `Latency × W + Cost × W + Failures × W`.
- **Policy Enforcement**: Automatically deprioritizes providers that exceed daily cost limits or have latency spikes.

### 🔍 Enhanced Repository Scanner
- **Deep Scanning**: Parses Python codebases to build a structural dependency graph.
- **Commit-Aware Versioning**: Tracks every scan with git commit hashes and stores historical snapshots.
- **Diff Engine**: Computes metric deltas (complexity, risk) and structural changes (added/removed symbols/files) between any two versions.
- **Interactive Visualization**: 2D force-directed graph of your codebase with diff-aware color coding.

### 🕵️‍♂️ Agentic Code Analysis
- **Autonomous Exploration**: A "Claude-Code" style agent that uses tools to explore, read, and analyze code.
- **Tool-Calling Loop**: Uses `read_file`, `search_code`, `list_files`, and `get_hotspots` to hunt for bugs or explain logic.
- **Multi-Repo Isolation**: Strictly isolated tool context ensuring accuracy across multiple concurrent scans.
- **Execution Engine**: Powered by `llama-3.3-70b-versatile` for high-fidelity reasoning.

### 💰 Real-Time Cost Dashboard
- **Live Budget Tracking**: Monitor daily provider spend and fallback rates.
- **Policy Config**: Visualize and adjust routing penalties and weights.

---

## 🚀 Quick Start

```bash
git clone https://github.com/utkarshgupta188/codeflux.git
cd codeflux

# 1. Configure
cp .env.example .env   
# Add your GROQ_API_KEY and OPENROUTER_API_KEY

# 2. Backend
pip install -r requirements.txt
# RECOMMENDED: Limit reload scope for stability during GitHub scans
uvicorn app.main:app --reload --reload-dir app

# 3. Frontend (separate terminal)
cd dashboard
npm install && npm run dev
```

## 📚 API Endpoints

### Repository Intelligence
| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/repo/scan` | AST scan of local path or GitHub URL |
| `GET`  | `/repo/{id}/versions` | List historical versions & commit hashes |
| `GET`  | `/repo/diff` | Compare metrics and structure between versions |
| `POST` | `/agent/run` | Execute the autonomous AI Agent loop |
| `POST` | `/repo/{id}/simulate-change` | BFS-based change impact analysis |

### AI Gateway
| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/chat` | Send AI prompt (auto-routed or manual override) |
| `GET`  | `/metrics/cost` | Real-time cost tracking & policy status |

## 🏗 Project Structure

```
app/
├── services/
│   ├── agent/          # Autonomous AI Agent & Tools
│   ├── scanner.py      # Version-aware repo scanner
│   ├── diff_service.py # Graph & Metric diffing engine
│   ├── graph_service.py # Versioned graph storage
│   └── router.py       # Cost-aware AI routing
└── main.py            # FastAPI Routes

dashboard/             # React + Vite + TailwindCSS
├── src/components/    
│   ├── AgentChat.tsx    # Autonomous Agent interface
│   ├── DiffViewer.tsx   # Version comparison UI
│   ├── RepoScanner.tsx  # Scanner with version history
│   └── CostDashboard.tsx # Budget & Policy tracking
```

## 🐳 Docker

```bash
docker-compose up --build
```
