# Implementation Plan

## Phase 1: Infrastructure
**Files:** `docker-compose.yml`
- Define `redis` service (alpine image) for Streams and Pub/Sub.
- Define `postgres` service (timescale/timescaledb image) for persistent time-series storage.
- Define internal Docker network `fleet-net` connecting all services.
- Define volumes for PG data and Redis append-only file.

## Phase 2: Ingestion Service (gRPC -> Redis Streams)
**Files:** `ingestion_service/server.py`, `ingestion_service/core/redis_client.py`
- Implement `telemetry_pb2_grpc.TelemetryServiceServicer`.
- Receive gRPC stream from `simulator`.
- Serialize each `TelemetryPoint` to a dict.
- Push to Redis Stream `telemetry:stream` using `XADD`.
- Must handle high throughput without blocking (asyncio or thread pool).

## Phase 3: Analytics Engine (CPU Bound)
**Files:** `analytics_engine/worker.py`, `analytics_engine/engine.py`, `analytics_engine/core/database.py`
- Run a worker loop consuming `telemetry:stream` via `XREADBLOCK`.
- Maintain a `collections.deque` (size N) per active `trip_id` for sliding window data.
- Compute rolling Z-score using NumPy to detect aggressive driving (e.g., sudden RPM/speed spikes).
- **On Anomaly:** Publish alert JSON to Redis Pub/Sub channel `alerts:live`.
- **Persistence:** Batch write processed telemetry to PostgreSQL `telemetry_data` table (configured as a TimescaleDB hypertable).

## Phase 4: API Service (I/O Bound SSE)
**Files:** `api_service/app/main.py`, `api_service/app/api/routers/alerts.py`
- FastAPI application.
- Implement `/api/alerts/stream` endpoint returning Server-Sent Events (`StreamingResponse`).
- Use an asyncio background task or async generator to subscribe to Redis Pub/Sub `alerts:live`.
- Yield events immediately to connected HTTP clients.

## Phase 5: Frontend Dashboard
**Files:** `frontend/src/hooks/useSSE.ts`, `frontend/src/App.tsx`
- Setup Zustand store to capture live state.
- Hook into `/api/alerts/stream` SSE endpoint.
- Use Chart.js Canvas API to draw 60 FPS live graphs for telemetry points.
- React DOM only updates on major events (like new trip starts or alert flags) to prevent thrashing.

## Phase 6: Orchestration
**Files:** `docker-compose.yml`
- Add build definitions for `ingestion_service`, `analytics_engine`, `api_service`, `frontend`, and `simulator`.
- Map ports (Frontend: 80, API: 8000, Ingestion: 50051).
- Set `depends_on` to ensure DB and Redis boot before services.

