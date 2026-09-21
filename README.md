# Fleet Fuel Saver — Real-Time Vehicle Telemetry & Anomaly Detection Platform

A distributed, horizontally-scalable data pipeline benchmarked to ingest and analyze **60,000+ telemetry points/min across 500 concurrent gRPC vehicle streams**, detect driving anomalies in real-time using statistical Z-Score analysis, and broadcast live alerts to a React dashboard over Server-Sent Events.

Built to demonstrate production-grade distributed systems engineering: async I/O, consumer group parallelism, atomic Redis pipelines, bulk database batching, and containerized microservice orchestration.

---

## Key Highlights

- **High-Throughput Ingestion** — Async gRPC server (`grpc.aio`) multiplexes 500+ concurrent vehicle streams on a single process
- **Distributed Stream Processing** — Redis Consumer Groups distribute workload across 3 parallel analytics workers with automatic load balancing and fault tolerance
- **Stateless Horizontal Scaling** — Sliding window state pushed to Redis, enabling `docker compose up --scale analytics=N` with zero code changes
- **Bulk Pipeline Optimization** — Single Redis pipeline executes 600+ commands per batch; `execute_batch` reduces Postgres round-trips by 99%
- **Real-Time Alerting** — Sub-second anomaly detection → Redis Pub/Sub → SSE → browser, with zero polling

---

## System Architecture

```text
┌─────────────────────────────────────────────────────────────────────────────┐
│                           DOCKER COMPOSE NETWORK                            │
│                                (fleet-net)                                  │
│                                                                             │
│  ┌──────────────┐     gRPC Stream      ┌───────────────────┐                │
│  │ Simulator    │ ───────────────────► │ Ingestion Service │                │
│  │ (CSV/Synth)  │   TelemetryPoint     │ (grpc.aio server) │                │
│  └──────────────┘    Proto3 Binary     └─────────┬─────────┘                │
│                                                  │                          │
│  ┌──────────────┐                                │ XADD                     │
│  │ Load Tester  │ ── gRPC Stream ───────────────►│ (maxlen=100k)            │
│  │ (500 cars)   │                                │                          │
│  └──────────────┘                                ▼                          │
│                                        ┌──────────────────┐                 │
│                                        │   Redis Stream   │                 │
│                                        │ telemetry:stream │                 │
│                                        └─────────┬────────┘                 │
│                                                  │                          │
│                                     XREADGROUP (analytics_group)            │
│                              ┌───────────────────┼───────────────────┐      │
│                              ▼                   ▼                   ▼      │
│                        ┌──────────┐        ┌──────────┐        ┌──────────┐ │
│                        │ Worker 1 │        │ Worker 2 │        │ Worker 3 │ │
│                        │ (engine) │        │ (engine) │        │ (engine) │ │
│                        └─────┬────┘        └─────┬────┘        └─────┬────┘ │
│                              │                   │                   │      │
│              ┌───────────────┴───────────────────┴───────────────────┘      │
│              │                                                              │
│              ├──► execute_batch ───► ┌──────────────────┐                   │
│              │    (bulk INSERT)      │ TimescaleDB      │                   │
│              │                       │ (PostgreSQL)     │                   │
│              │                       │ - telemetry_data │                   │
│              │                       │ - alerts         │                   │
│              │                       └────────┬─────────┘                   │
│              │                                │                             │
│              │                                │ SQL queries                 │
│              │                                ▼                             │
│              │   PUBLISH alerts:live ┌──────────────────┐                   │
│              ├──────────────────────►│  FastAPI + SSE   │                   │
│              │                       │  (api_service)   │                   │
│              │                       └────────┬─────────┘                   │
│              │                                │                             │
│              │                                │ EventSource                 │
│              │                                ▼                             │
│              │                       ┌──────────────────┐                   │
│              │                       │  React Frontend  │                   │
│              │                       │   (Vite + TS)    │                   │
│              │                       └──────────────────┘                   │
│              │                                                              │
│              └──► XACK (acknowledge processed messages)                     │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Data Flow

```
  ① GENERATE            ② INGEST              ③ BUFFER              ④ PROCESS
┌───────────┐       ┌──────────────┐      ┌──────────────┐     ┌──────────────┐
│ Kaggle CSV │──────►│ gRPC Server  │─────►│ Redis Stream │────►│ 3x Analytics │
│ 5M points  │ gRPC  │ (async I/O)  │ XADD │ telemetry:   │GROUP│   Workers    │
│ 35 sensors │stream │ multiplexed  │      │   stream     │     │ (stateless)  │
└───────────┘       └──────────────┘      └──────────────┘     └──────┬───────┘
                                                                       │
                    ⑦ DISPLAY             ⑥ STREAM             ⑤ PERSIST & ALERT
               ┌──────────────┐      ┌──────────────┐     ┌──────────────┐
               │ React + Vite │◄─────│ FastAPI SSE  │◄────│ Redis Pub/Sub│
               │  Live Alerts │ SSE  │ /alerts/     │ SUB │ alerts:live  │
               │  Charts      │      │   stream     │     │              │
               │  Bookmarks   │      │ /history/*   │◄────│ TimescaleDB  │
               └──────────────┘      └──────────────┘ SQL └──────────────┘
```

---

## Anomaly Detection Rules

| Rule | Condition | Severity | Description |
|------|-----------|----------|-------------|
| **OVERSPEEDING** | `speed > 60 km/h` | 🔴 HIGH | Vehicle exceeds fleet speed policy |
| **IDLE_REVVING** | `speed < 20 km/h` AND `rpm > 2000` | 🟠 MEDIUM | High engine revs while stationary — wastes fuel |
| **AGGRESSIVE_ACCELERATION** | `\|Z-Score\| > 1.5` (rolling window of 20 RPM readings) | 🔴 HIGH | Sudden RPM spike detected via statistical outlier analysis |

Z-Score sliding windows are maintained in Redis Lists (`window:<trip_id>`) using atomic pipelines, making the engine fully **stateless** and safe for horizontal scaling.

---

## Tech Stack

| Layer | Technology | Purpose |
|-------|-----------|---------|
| **Transport** | gRPC + Protocol Buffers (proto3) | High-performance binary streaming from IoT simulators |
| **Ingestion** | Python `grpc.aio` | Async multiplexed server handling 500+ concurrent streams |
| **Message Queue** | Redis Streams | Durable, ordered event buffer with consumer group support |
| **Processing** | Redis Consumer Groups | Distributed work partitioning with at-least-once delivery |
| **State** | Redis Pipelines + Lists | Atomic sliding window operations for Z-Score computation |
| **Analytics** | NumPy | Vectorized mean/std/Z-Score statistical calculations |
| **Database** | TimescaleDB (PostgreSQL) | Time-series hypertables with automatic 7-day retention |
| **Broadcast** | Redis Pub/Sub | Fire-and-forget alert fan-out to API instances |
| **API** | FastAPI + Uvicorn | Async REST endpoints and SSE streaming |
| **Real-Time** | Server-Sent Events (SSE) | Unidirectional push from server to browser |
| **Frontend** | React 18 + TypeScript + Vite | Live dashboard with tabs, charts, and bookmarks |
| **State Mgmt** | Zustand | Lightweight stores for live alerts and persistent bookmarks |
| **Charts** | Chart.js + react-chartjs-2 | Historical alert distribution bar charts |
| **Orchestration** | Docker Compose | Multi-container deployment with networking and volumes |

---

## Project Structure

```
Fleet_Fuel_Saver/
│
├── docker-compose.yml              # Orchestrates all 7 services, networks, and volumes
│
├── protos/
│   └── telemetry.proto             # gRPC service & message schema (TelemetryPoint, StreamTelemetry)
│
├── shared/                         # Reusable Python packages installed via pip in Dockerfiles
│   ├── shared_proto/               # Compiled protobuf stubs (telemetry_pb2.py, telemetry_pb2_grpc.py)
│   │   ├── pyproject.toml          # Package config for pip install
│   │   └── shared_proto/
│   │       ├── __init__.py
│   │       ├── telemetry_pb2.py    # Auto-generated protobuf message classes
│   │       └── telemetry_pb2_grpc.py # Auto-generated gRPC stubs & servicer interfaces
│   │
│   └── shared_redis/               # Centralized Redis connection pool factory
│       ├── pyproject.toml
│       └── shared_redis/
│           ├── __init__.py         # Exports get_redis_client, get_async_redis_client
│           └── client.py           # Sync + async Redis connection pools (prevents connection churn)
│
├── data/
│   └── vehicle_data.csv            # 869 MB Kaggle dataset — 5M rows, 35 sensor columns
│
├── simulator/                      # IoT vehicle simulator (data source)
│   ├── Dockerfile
│   ├── requirements.txt            # grpcio, grpcio-tools
│   ├── config.py                   # Reads INGESTION_HOST, TICK_RATE_MS from env
│   └── main.py                     # Streams CSV rows as gRPC TelemetryPoints to ingestion
│
├── ingestion_service/              # gRPC gateway → Redis Stream
│   ├── Dockerfile
│   ├── requirements.txt            # grpcio, grpcio-tools, redis
│   └── server.py                   # Async gRPC server (grpc.aio), XADD to telemetry:stream
│
├── analytics_engine/               # Distributed stream processor (3 replicas)
│   ├── Dockerfile
│   ├── requirements.txt            # redis, numpy, psycopg2-binary
│   ├── core/
│   │   ├── config.py               # Configuration placeholder
│   │   └── database.py             # Postgres connection, schema init (hypertables, retention)
│   ├── engine.py                   # RuleEngine: batch anomaly evaluation with Redis pipelines
│   └── worker.py                   # Consumer group reader, bulk Postgres inserts, Pub/Sub alerts
│
├── api_service/                    # REST API + SSE streaming gateway
│   ├── Dockerfile
│   ├── requirements.txt            # fastapi, uvicorn, redis, psycopg2-binary, sse-starlette
│   └── app/
│       ├── main.py                 # FastAPI app, CORS middleware, router mounting
│       └── api/routers/
│           ├── alerts.py           # GET /alerts/stream — SSE via Redis Pub/Sub subscription
│           └── history.py          # GET /history/alerts, /stats, /timeseries — TimescaleDB queries
│
├── frontend/                       # React dashboard (Vite + TypeScript)
│   ├── Dockerfile
│   ├── package.json                # react, zustand, chart.js, react-chartjs-2, vite, typescript
│   ├── vite.config.ts              # Dev server on 0.0.0.0:5173, React plugin
│   ├── tsconfig.json               # ES2020, strict mode, bundler resolution
│   ├── index.html                  # SPA entry point
│   └── src/
│       ├── main.tsx                # ReactDOM render into #root
│       ├── App.tsx                 # Dashboard: Live Alerts | Historical Charts | Bookmarks tabs
│       ├── hooks/
│       │   └── useSSE.ts           # EventSource hook → subscribes to /alerts/stream
│       └── store/
│           ├── useFleetStore.ts    # Zustand store: latest 100 live alerts (in-memory)
│           └── useBookmarkStore.ts # Zustand store: starred trip IDs (persisted to localStorage)
│
└── load_test/                      # Concurrent stress testing harness
    ├── Dockerfile
    ├── requirements.txt            # grpcio, grpcio-tools
    └── main.py                     # Async gRPC load test: 500 vehicles × 60 sec × 2 points/sec
```

---

## Getting Started

### Prerequisites

- [Docker](https://docs.docker.com/get-docker/) and [Docker Compose](https://docs.docker.com/compose/install/) v2+
- ~1 GB free disk space (+ 869 MB for the Kaggle dataset)

### 1. Clone & Add Dataset

```bash
git clone https://github.com/TheOne969/Fleet_Fuel_Saver.git
cd Fleet_Fuel_Saver
```

Download the [Vehicle Energy & Telemetry Dataset](https://www.kaggle.com/datasets/yashdev01/vehicle-energy-and-telemetry-dataset) from Kaggle and place the CSV file at `data/vehicle_data.csv`.

### 2. Launch All Services

```bash
docker compose up --build -d
```

This spins up 9 containers:
| Container | Description |
|-----------|-------------|
| `redis` | Event stream buffer + sliding window state + Pub/Sub |
| `postgres` | TimescaleDB for time-series storage with 7-day retention |
| `ingestion` | Async gRPC server on port `50051` |
| `analytics` ×3 | Distributed consumer group workers |
| `api` | FastAPI on port `8000` (REST + SSE) |
| `simulator` | Streams Kaggle dataset via gRPC |
| `frontend` | React dashboard on port `5173` |

### 3. Open the Dashboard

Navigate to **[http://localhost:5173](http://localhost:5173)** to see live alerts streaming in real-time.

### 4. View API Docs

FastAPI auto-generates interactive documentation at **[http://localhost:8000/docs](http://localhost:8000/docs)**.

### 5. Resetting the Database (Optional)

If you run multiple load tests or want to wipe all historical data and start completely fresh, you can destroy the containers and their persistent volumes, then restart them:

```bash
# Bring down the system and delete the Postgres/Redis volumes
docker compose down -v

# Start fresh
docker compose up -d
```

---

## Load Testing

A standalone load testing harness simulates hundreds of concurrent vehicles sending aggressive driving telemetry:

```bash
# Build the load tester image
docker build -t load_test -f load_test/Dockerfile .

# Run 500 concurrent vehicles for 60 seconds (~59,000 data points)
docker run --rm \
  --network fleet_fuel_saver_fleet-net \
  -e NUM_VEHICLES=500 \
  -e TEST_DURATION_SEC=60 \
  load_test
```

### Sample Output

```
Starting Load Test with 500 concurrent vehicles for 60 seconds...
Target Host: ingestion:50051
========================================
LOAD TEST COMPLETE
Target Concurrent Vehicles: 500
Successful Connections (Streams closed cleanly): 500
Failed Connections: 0
Total Points Sent: 59008
Total Unhandled Errors: 0
========================================
```

---

## Key Engineering Decisions

### Why `grpc.aio` over `ThreadPoolExecutor`?
The ingestion service is purely I/O-bound (gRPC → Redis). Python's GIL means `ThreadPoolExecutor` threads still execute on a single core. `grpc.aio` multiplexes all 500+ streams on one event loop without spawning OS threads, eliminating context-switching overhead entirely.

### Why Redis Streams over Kafka?
For a single-node deployment, Redis Streams provide the same consumer group semantics (competing consumers, at-least-once delivery, pending entry lists) without the operational complexity of a Kafka cluster, ZooKeeper, or topic partitioning configuration.

### Why are sliding windows in Redis instead of Python memory?
Storing Z-Score windows in local Python `deque` objects would make the analytics engine **stateful** — if a container crashes, its window data is lost, and you cannot add more replicas without data inconsistency. Pushing state to Redis Lists makes each worker completely interchangeable.

### Why Redis Pipelines for Z-Score evaluation?
Without pipelines, evaluating 200 points requires 600 individual network round-trips to Redis (3 commands × 200 points). A single `pipeline.execute()` call batches all 600 commands into one TCP packet, reducing latency from ~600ms to ~3ms per batch.

### Why `execute_batch` over individual INSERTs?
A single `cursor.execute()` per row means 200 TCP round-trips to Postgres per batch. `psycopg2.extras.execute_batch` packs them into a single network call, achieving ~30x throughput improvement.

### Why no Unique Constraints on telemetry data?
The system embraces an **Append-Only** philosophy to prioritize massive write throughput over strict idempotency. Enforcing a `UNIQUE(trip_id, time)` index across a TimescaleDB hypertable with billions of rows incurs a massive "index tax," requiring the DB to verify uniqueness before every insert. In the rare event a worker crashes before sending an `XACK` to Redis (At-Least-Once Delivery), it may insert a duplicate batch. In large-scale IoT architectures, this minor duplication is an acceptable trade-off to prevent ingestion bottlenecks.

### Why SSE over WebSockets?
The alert stream is unidirectional (server → browser). SSE is simpler, auto-reconnects natively, works over standard HTTP, and doesn't require a WebSocket upgrade handshake. It's the right tool for a push-only channel.

---

## Dataset

**Source:** [Vehicle Energy & Telemetry Dataset](https://www.kaggle.com/datasets/yashdev01/vehicle-energy-and-telemetry-dataset) (Kaggle)

| Attribute | Value |
|-----------|-------|
| Rows | 5,000,000 |
| Columns | 35 |
| File Size | 869 MB |
| Key Fields Used | `Trip`, `Vehicle Speed[km/h]`, `Engine RPM[RPM]`, `Latitude[deg]`, `Longitude[deg]`, `Gradient` |

---

## License

This project is for educational and portfolio demonstration purposes.

