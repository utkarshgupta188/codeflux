# AI Gateway Features

## 1. Core Reliability & Routing
- **Primary-Fallback Architecture**: Automatically routes traffic to **Groq** (Primary) for low-latency inference.
- **Automatic Failover**: Instantly switches to **OpenRouter** if the primary provider fails (e.g., downtime, rate limits, API errors), ensuring high availability.
- **Error Handling**: Gracefully manages upstream errors (4xx/5xx) and normalized error responses (502 Bad Gateway) only when all providers fail.

## 2. High-Performance Architecture
- **Fully Asynchronous**: Built on **FastAPI** and **asyncio**, allowing high concurrency without blocking on I/O.
- **Non-Blocking Logging**: Request telemetry (latency, provider, model) is decoupled from the response path using **FastAPI BackgroundTasks**. Database writes never delay the API response to the user.
- **Connection Pooling**: Uses `SQLAlchemy` async engine with persistent connection pooling for efficient database access.

## 3. Extensibility & Design
- **Adapter Pattern**: strict separation of concerns using `BaseModelAdapter`. New providers (e.g., Anthropic, Vertex AI) can be added by implementing a single `generate` method.
- **Unified API Schema**: Abducts complexity from the client. Clients send a standardized `ChatRequest` and receive a `ChatResponse`, regardless of which underlying provider served the request.
- **Type-Safe Configuration**: Uses `pydantic-settings` for robust environment variable validation and management.

## 4. Observability & Data
- **Structured Logging**: Every request is persisted to **PostgreSQL** (production) or **SQLite** (dev) with:
    - Input Prompt
    - Provider Used (tracking fallback rates)
    - Model Version
    - End-to-End Latency (ms)
    - Timestamp
- **Granular Latency Tracking**: Captures precise execution time for performance monitoring.

## 5. Deployment & Security
- **Containerized**: Production-ready `Dockerfile` (distroless/slim optimization accessible).
- **Environment Isolation**: API keys and DB credentials managed strictly via `.env` / environment variables.
- **Database Flexibility**: Supports `PostgreSQL` for production scale and `SQLite` for local development without code changes (via `SQLAlchemy` dialect switching).
