# Backend Architecture

## Layered design

```
Client (UI / SIEM)
    │
    ▼
FastAPI (async HTTP + WebSocket)
    │
    ├── Middleware: CORS, rate limit, security headers, request ID
    ├── JWT auth (role-based: admin, analyst, viewer)
    │
    ▼
API routers (/api/v1/*)
    │
    ▼
Services
    ├── DetectionService   — orchestration
    ├── FlowBufferService  — streaming windows (hash map + deque)
    ├── GraphService       — PyG graph build
    ├── InferenceEngine    — GCN / GAT / RF
    ├── AlertService       — alerts + WebSocket push
    ├── MetricsService     — aggregates
    └── CacheService       — optional Redis
    │
    ▼
Repositories → SQLite (PostgreSQL-ready)
```

## Real-time pipeline

1. Client sends flows to `POST /predict`
2. Flows ingested into per-victim buffer (queue)
3. When enough flows exist, graph is built (hash map IP indexing)
4. GCN/GAT forward pass → probability
5. Prediction stored; alert if above threshold
6. WebSocket broadcast to `alerts`, `graph`, `traffic` channels

## Security

- Bcrypt password hashing
- JWT bearer tokens
- Role-based route guards
- Input validation (Pydantic)
- Rate limiting per IP
- TLS termination at reverse proxy (nginx / cloud LB)

## Deployment

- **Dev:** uvicorn reload
- **Prod:** Docker + gunicorn/uvicorn workers behind nginx
- **Scale:** horizontal API replicas; Redis for shared cache; PostgreSQL for DB
