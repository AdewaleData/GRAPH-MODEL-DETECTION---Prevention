# Real-Time DDoS Attack Detection & Prevention Using Graph Neural Networks

Final Year Project pipeline on the **CICDDoS2019** dataset (`CICDDoS.csv`).

**Detection:** GCN/GAT graph-window classification  
**Prevention:** Automated graph-driven mitigation (block / rate-limit / quarantine)

## Quick Start

### ML notebook
```bash
pip install -r requirements.txt
jupyter notebook notebooks/CICDDoS_GNN_DDoS_Detection.ipynb
```

### Local dev (API + dashboard separately)
```bash
pip install -r backend/requirements.txt -r requirements.txt
cd backend && uvicorn app.main:app --reload --port 8000
cd frontend && npm install && npm run dev
```

### Production-style deploy (Docker Compose)
```bash
cp .env.production.example .env   # edit domain + JWT_SECRET
chmod +x scripts/deploy-production.sh
./scripts/deploy-production.sh
# Dashboard: http://<server-ip>/  ·  Prevention: /prevention
```

**Full production guide:** [PRODUCTION.md](PRODUCTION.md)  
**Architecture & cloud matrix:** [DEPLOYMENT.md](DEPLOYMENT.md)

Run notebook cells top-to-bottom. Artifacts are written to `artifacts/models` and `artifacts/figures`.

## Structure

| Path | Description |
|------|-------------|
| `CICDDoS.csv` | Dataset (place in project root) |
| `src/ddos_gnn/` | Modular Python package |
| `notebooks/` | Main FYP notebook |
| `backend/` | FastAPI API + prevention engine |
| `frontend/` | Next.js SOC dashboard |
| `deploy/` | NGINX config |
| `artifacts/` | Models & figures (created at runtime) |

## Models

- Random Forest & XGBoost (per-flow baselines)
- GCN & GAT (batched **graph-window** classification with edge features, focal loss, threshold tuning)
- Multi-seed experiments + bootstrap CI + McNemar significance tests

See `EXPERIMENTS.md` for the evaluation protocol.

## Prevention

When the GNN detects an attack, the **MitigationService** ranks attacker source IPs from the traffic graph and applies:

- **Critical** → block top 5 sources  
- **High** → rate-limit top 3  
- **Medium** → quarantine top 2  

Modes: `simulated` (default), `iptables` (Linux gateway), `webhook` (SIEM/SOAR).

Dashboard: `/prevention` · API: `/api/v1/mitigation/*`

## Requirements

Python 3.10+, Node 20+, Docker optional. See `requirements.txt`.
