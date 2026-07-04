# Halal Graph — DDoS Detection & Prevention API

Production FastAPI backend for real-time GNN-based DDoS detection with automated graph-driven prevention.

## Live demo stream

On startup the API runs a **live simulator** that feeds real CICDDoS2019 flow windows through GCN/GAT every few seconds. Metrics, traffic logs, graphs, and alerts populate automatically — no manual `/predict` calls needed.

## Quick start

```bash
pip install -r backend/requirements.txt -r requirements.txt
cd backend
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Open **http://localhost:8000/docs**

Default admin (first startup):

- Email: `admin@gmail.com`
- Password: `Admin@12345`

Set `JWT_SECRET` in environment for production.

## API endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/health` | Service + model status |
| POST | `/api/v1/auth/register` | Register user |
| POST | `/api/v1/auth/login` | JWT login |
| GET | `/api/v1/auth/me` | Current user |
| POST | `/api/v1/predict` | Run GNN/RF detection |
| GET | `/api/v1/metrics` | Detection summary |
| GET | `/api/v1/metrics/history` | Prediction history |
| GET | `/api/v1/alerts` | List alerts |
| POST | `/api/v1/alerts/acknowledge` | Ack alert |
| GET | `/api/v1/graph/live/{victim_ip}` | Live graph snapshot |
| GET | `/api/v1/graph/victims` | Buffered victims |
| GET | `/api/v1/mitigation/active` | Active prevention rules |
| GET | `/api/v1/mitigation/history` | Mitigation audit log |
| GET | `/api/v1/mitigation/summary` | Prevention statistics |
| POST | `/api/v1/mitigation/apply` | Manual block/rate-limit |
| POST | `/api/v1/mitigation/revoke` | Revoke prevention rule |

## Prevention

When GNN detection fires an alert, **MitigationService** ranks attacker sources from the traffic graph and auto-applies:

- **Critical** (≥85%) → block top 5 IPs
- **High** (≥65%) → rate-limit top 3 IPs
- **Medium** (≥62%) → quarantine top 2 IPs

Environment:

```env
MITIGATION_AUTO_ENABLED=true
MITIGATION_MODE=simulated   # simulated | iptables | webhook
MITIGATION_WEBHOOK_URL=     # for SOAR integration
```

Blocked sources are filtered at ingest (`MITIGATION_FILTER_BLOCKED_FLOWS=true`).

See **[DEPLOYMENT.md](../DEPLOYMENT.md)** for where to deploy each component.

## WebSockets

| Path | Stream |
|------|--------|
| `/ws/alerts` | Live DDoS alerts |
| `/ws/graph` | Graph structure updates |
| `/ws/traffic` | Prediction events |
| `/ws/metrics` | System heartbeat / metrics |
| `/ws/mitigation` | Prevention apply/revoke events |

## Docker

```bash
docker compose up --build
```

## Architecture

See `docs/BACKEND_ARCHITECTURE.md` in project root.

## DSA mapping

- **Graph** — PyG communication graphs per victim window
- **Hash map** — flow buffer keyed by destination IP; rate limiter per client
- **Queue** — deque per victim for sliding windows
- **Cache** — optional Redis for prediction deduplication
- **Async event loop** — FastAPI + WebSocket broadcasts
