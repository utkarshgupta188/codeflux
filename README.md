# CodeFlux — AI Gateway & Code Intelligence Engine

A production-grade AI Gateway with intelligent routing, real-time observability, and AST-based code analysis — built with FastAPI + React.

## 🌟 Key Features

### 🤖 AI Routing Gateway
- **Multi-Provider Support**: Groq (primary) + OpenRouter (fallback) with automatic failover.
- **Cost-Aware Intelligent Routing**: Routes based on a scoring formula: `Latency × W + Cost × W + Failures × W`.
- **Policy Enforcement**: Automatically deprioritizes providers that exceed daily cost limits or have latency spikes.

### 🔍 Intelligent Repository Scanner
- **Deep Scanning**: Parses Python codebases to build a structural dependency list.
- **Metrics Extraction**: Analyzes code for symbols, files, and dependencies to provide health metrics.
- **Local & GitHub Support**: Works with both local directories and remote Git repositories.

### 📝 Professional README Generator
- **AI-Powered Analysis**: Automatically reads your codebase to generate a complete README.
- **Premium Formatting**: Produces beautiful Markdown with badges, structured sections, and emojis.
- **Dedicated UI**: A specialized dashboard section to generate, preview, and copy your documentation in seconds.

### 🕵️‍♂️ Agentic Code Analysis
- **Autonomous Exploration**: A "Claude-Code" style agent that uses tools to explore, read, and analyze code.
- **Tool-Calling Loop**: Uses `read_file`, `search_code`, `list_files`, and `get_hotspots` to hunt for bugs or explain logic.
- **Multi-Repo Isolation**: Strictly isolated tool context ensuring accuracy across multiple concurrent scans.
- **Execution Engine**: Powered by `llama-3.3-70b-versatile` for high-fidelity reasoning.


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

### Repository & Documentation
| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/repo/scan` | AST scan of local path or GitHub URL |
| `GET`  | `/repo/{scan_id}/status` | Get current scan status |
| `GET`  | `/repo/{scan_id}/health` | Retrieve codebase health metrics |
| `POST` | `/repo/{scan_id}/generate-readme` | Generate professional Markdown documentation |
| `POST` | `/agent/run` | Execute the autonomous AI Agent loop |

### AI Gateway
| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/chat` | Send AI prompt (auto-routed or manual override) |

## 🏗 Project Structure

```
app/
├── services/
│   ├── agent/          # Autonomous AI Agent & Tools
│   ├── scanner.py      # AST repository scanner
│   ├── readme_service.py # Professional README generator
│   └── router.py       # Cost-aware AI routing
└── main.py            # FastAPI Routes

dashboard/             # React + Vite + TailwindCSS
├── src/components/    
│   ├── AgentChat.tsx    # Autonomous Agent interface
│   ├── ReadmeGen.tsx    # Dedicated README generator
│   └── RepoScanner.tsx  # Repository health scanner
```

## 🐳 Docker

```bash
docker-compose up --build
```
