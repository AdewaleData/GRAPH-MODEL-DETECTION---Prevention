# Deployment Guide — Halal Graph DDoS Detection & Prevention

This document describes where each component runs and how to deploy the full stack for thesis demos, lab environments, and production-shaped SOC deployments.

## Architecture

```
                    ┌─────────────────────────────────────────┐
                    │  NGINX (reverse proxy) — port 80/443     │
                    │  TLS termination · routing · WS upgrade  │
                    └───────────┬─────────────┬───────────────┘
                                │             │
                    /api/* /ws/*│             │ /*
                                ▼             ▼
                    ┌──────────────────┐  ┌──────────────────┐
                    │  FastAPI API      │  │  Next.js Dashboard│
                    │  GNN inference    │  │  SOC UI           │
                    │  Prevention engine│  │  Prevention panel │
                    └────────┬─────────┘  └──────────────────┘
                             │
              ┌──────────────┼──────────────┐
              ▼              ▼              ▼
        ┌──────────┐  ┌──────────┐  ┌──────────────┐
        │  Redis   │  │  SQLite  │  │  ML Models   │
        │  cache   │  │  alerts  │  │  artifacts/  │
        └──────────┘  │  mitigations│  models/    │
                      └──────────┘  └──────────────┘
```

## Component Deployment Matrix

| Component | What it does | Where to deploy | Port | Notes |
|-----------|--------------|-----------------|------|-------|
| **NGINX** | Reverse proxy, TLS, WebSocket upgrade | Edge VM / cloud load balancer / same host as stack | 80, 443 | Public-facing entry point |
| **FastAPI (`api`)** | GNN detection, prevention engine, REST + WS | Private subnet / Docker network / K8s pod | 8000 (internal) | Never expose directly in prod |
| **Next.js (`frontend`)** | SOC dashboard, prevention UI | Same cluster as API, behind NGINX | 3000 (internal) | Build with `NEXT_PUBLIC_API_URL` |
| **Redis** | Prediction cache, session scaling | Co-located with API or managed Redis | 6379 (internal) | Optional but recommended |
| **SQLite / DB** | Predictions, alerts, mitigation audit log | Volume on API host (`artifacts/backend/`) | — | Use PostgreSQL for multi-instance prod |
| **ML artifacts** | `gcn_best.pt`, `gat_best.pt`, `rf_bundle.joblib` | Read-only volume mounted into API | — | Train via notebook first |
| **iptables actuator** | Real network blocking (optional) | **Linux bare metal or privileged container** on traffic path | — | `MITIGATION_MODE=iptables` |
| **Webhook actuator** | SOAR / Splunk / Elastic integration | API posts to your SIEM URL | — | `MITIGATION_MODE=webhook` |

## Quick Start — Docker Compose (recommended for demo & thesis defense)

**Deploy on:** Any Linux/macOS/Windows host with Docker Desktop, cloud VM (AWS EC2, Azure VM, DigitalOcean), or university lab server.

```bash
# 1. Train models (once) — local dev machine or CI
pip install -r requirements.txt
jupyter notebook notebooks/CICDDoS_GNN_DDoS_Detection.ipynb

# 2. Configure
cp .env.example .env
# Edit JWT_SECRET and NEXT_PUBLIC_API_URL (public URL of your server)

# 3. Deploy full stack
docker compose up --build -d

# 4. Access
# Dashboard:  http://<server-ip>/
# API docs:   http://<server-ip>/docs
# Login:      admin@gmail.com / Admin@12345  (change immediately)
```

## Deployment Scenarios

### 1. Local development (your laptop)

| Service | Command | URL |
|---------|---------|-----|
| API | `cd backend && uvicorn app.main:app --reload --port 8000` | http://127.0.0.1:8000 |
| Frontend | `cd frontend && npm run dev` | http://localhost:3000 |
| Prevention | Auto-enabled; simulated mode | `/prevention` page |

Set `NEXT_PUBLIC_API_URL=http://127.0.0.1:8000` in `frontend/.env.local` for dev.

### 2. University lab / thesis demo server

**Deploy on:** Single Ubuntu 22.04 VM (4 GB RAM, 2 vCPU minimum).

```bash
docker compose up --build -d
```

- **NGINX** → public port 80 — audience accesses dashboard here
- **API + prevention** → internal Docker network
- **Simulated mitigation** → safe for demo; shows block rules in UI without touching network

For defense day: enable `LIVE_SIMULATOR_ENABLED=true` so attack traffic replays automatically and prevention triggers live.

### 3. Cloud production-shaped deployment

**Deploy on:** AWS, Azure, or GCP.

| Layer | AWS | Azure | GCP |
|-------|-----|-------|-----|
| Edge / TLS | ALB + ACM certificate | App Gateway + cert | Cloud Load Balancing + managed cert |
| NGINX / routing | EC2 or ECS sidecar | Container Apps ingress | GCE MIG or Cloud Run ingress |
| API containers | ECS Fargate / EKS | AKS / Container Apps | Cloud Run / GKE |
| Frontend | S3 + CloudFront **or** same ECS | Static Web Apps **or** AKS | Cloud Run |
| Redis | ElastiCache | Azure Cache for Redis | Memorystore |
| Database | RDS PostgreSQL (replace SQLite) | Azure Database | Cloud SQL |
| Models | EFS / S3 mount into API | Azure Files | GCS FUSE |

**Environment variables for cloud API:**

```env
JWT_SECRET=<strong-secret>
MITIGATION_AUTO_ENABLED=true
MITIGATION_MODE=webhook
MITIGATION_WEBHOOK_URL=https://your-siem.example.com/halal-graph/events
REDIS_URL=redis://your-redis-host:6379/0
CORS_ORIGINS=https://dashboard.yourdomain.com
LIVE_SIMULATOR_ENABLED=false
```

### 4. On-prem SOC / network edge (real prevention)

**Deploy on:** Linux server inline with network traffic or with SPAN/tap flow export.

| Component | Location |
|-----------|----------|
| Flow collector (Zeek, nProbe, or custom) | Network edge — exports flows to API `POST /api/v1/predict` |
| **API + GNN** | SOC VLAN — private IP |
| **Prevention (`iptables`)** | **Same Linux gateway** that routes victim traffic — requires root |
| **Dashboard** | SOC analyst workstations via internal NGINX |

Enable real blocking:

```env
MITIGATION_MODE=iptables
MITIGATION_AUTO_ENABLED=true
```

Run API container with:

```yaml
cap_add:
  - NET_ADMIN
network_mode: host  # only when API is on the gateway itself
```

### 5. Kubernetes (optional scale-out)

| Resource | Replicas | Notes |
|----------|----------|-------|
| `Deployment/halal-api` | 2+ | Shared Redis + PostgreSQL; mount models PVC |
| `Deployment/halal-frontend` | 2+ | Stateless |
| `Ingress` | 1 | TLS + `/api` + `/ws` routing |
| `Service/redis` | 1 | Or managed Redis |
| `CronJob/mitigation-expire` | — | Future: auto-revoke after TTL |

## Prevention Modes

| Mode | Deploy where | Use case |
|------|--------------|----------|
| `simulated` (default) | Any Docker host | Thesis demo, dev — rules in DB + dashboard |
| `iptables` | Linux gateway / privileged container | Lab PoC with real drops |
| `webhook` | API anywhere | Enterprise SIEM/SOAR integration |

### Policy (automatic)

| Alert severity | GNN probability | Action | Top sources blocked |
|----------------|-----------------|--------|---------------------|
| Critical | ≥ 85% | **BLOCK** | Top 5 attacker IPs from graph |
| High | ≥ 65% | **RATE_LIMIT** | Top 3 |
| Medium | ≥ 62% | **QUARANTINE** | Top 2 |

## API Endpoints (Prevention)

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/v1/mitigation/active` | Active prevention rules |
| GET | `/api/v1/mitigation/history` | Audit trail |
| GET | `/api/v1/mitigation/summary` | Stats for dashboard |
| POST | `/api/v1/mitigation/apply` | Manual block (analyst) |
| POST | `/api/v1/mitigation/revoke` | Revoke rule |
| WS | `/ws/mitigation` | Real-time prevention events |

## Pre-deployment Checklist

- [ ] Models exist in `artifacts/models/` (run notebook)
- [ ] `JWT_SECRET` changed from default
- [ ] Default admin password changed after first login
- [ ] `NEXT_PUBLIC_API_URL` set to public origin (no trailing slash)
- [ ] TLS configured on NGINX / load balancer for production
- [ ] `LIVE_SIMULATOR_ENABLED=false` in production (use real flow ingest)
- [ ] Backup volume for `artifacts/backend/ddos.db`

## Monitoring

- **Health:** `GET /health`
- **Metrics:** `GET /api/v1/metrics` — includes `active_mitigations`, `flows_blocked`, `avg_time_to_mitigate_ms`
- **Dashboard:** `/prevention` — live rules, MTTM, audit log
