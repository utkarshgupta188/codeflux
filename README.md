# Codeflux AI Gateway

A production-grade, high-performance AI Gateway built with FastAPI, supporting intelligent routing, fallback strategies, and comprehensive observability.

## Features

- **Multi-Provider Support**: 
  - Primary: **Groq** (Low latency, Llama 3)
  - Fallback: **OpenRouter** (High availability, GPT-4/Claude/etc)
- **Resilient Architecture**: Automatic failover ensures 99.9% uptime for AI features.
- **Observability Layer**: 
  - Real-time metrics endpoint (`/metrics/summary`)
  - Tracks Latency (Avg, P95), Request Counts, and Provider Splits.
  - Granular logging to PostgreSQL (production) or SQLite (dev).
- **Async High-Concurrency**: Built on `asyncio` and `SQLAlchemy[async]`.
- **Developer Ready**: Dockerized, typed configuration, and clear validation.

## Quick Start

1.  **Clone the repository**:
    ```bash
    git clone https://github.com/utkarshgupta188/codeflux.git
    cd codeflux
    ```

2.  **Configure Environment**:
    ```bash
    cp .env.example .env
    # Edit .env with your API Keys
    ```

3.  **Run with Docker**:
    ```bash
    docker-compose up --build
    ```
    
    *Or run locally:*
    ```bash
    pip install -r requirements.txt
    uvicorn app.main:app --reload
    ```

## Usage

**Chat endpoint**:
```bash
curl -X POST "http://localhost:8000/chat" \
     -H "Content-Type: application/json" \
     -d '{
           "prompt": "Explain quantum computing",
           "task_type": "explanation"
         }'
```

**Metrics Endpoint**:
```bash
curl "http://localhost:8000/metrics/summary?range=last_24h"
```

## Structure
- `app/adapters`: LLM Provider implementations.
- `app/services`: Core logic (Router, Logger, Metrics).
- `app/models`: Database and API schemas.
