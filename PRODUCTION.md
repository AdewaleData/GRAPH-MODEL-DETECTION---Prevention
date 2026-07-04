# Production Deployment — Halal Graph

One-page guide to deploy on a **Linux cloud VM** (AWS EC2, Azure, DigitalOcean, university server).

## Requirements

| Resource | Minimum |
|----------|---------|
| OS | Ubuntu 22.04 LTS |
| RAM | 4 GB |
| CPU | 2 vCPU |
| Disk | 20 GB |
| Software | Docker 24+ & Docker Compose v2 |

## Step 1 — Provision server & open ports

| Port | Purpose |
|------|---------|
| **80** | HTTP (dashboard + API) |
| **443** | HTTPS (after TLS setup) |
| **22** | SSH (your IP only) |

## Step 2 — Upload project

```bash
ssh user@YOUR_SERVER_IP

# Option A: git clone
git clone <your-repo-url> halal-graph && cd halal-graph

# Option B: scp from your laptop
# scp -r Halal-Graph-Model user@YOUR_SERVER_IP:~/halal-graph
```

Ensure `artifacts/models/` contains `gcn_best.pt`, `gat_best.pt`, `rf_bundle.joblib`.

## Step 3 — Configure environment

```bash
cp .env.production.example .env
nano .env
```

Set these **required** values:

```env
NEXT_PUBLIC_API_URL=https://your-domain.com
CORS_ORIGINS=https://your-domain.com
JWT_SECRET=<run: openssl rand -hex 32>
LIVE_SIMULATOR_ENABLED=false
PRODUCTION=true
```

## Step 4 — Deploy

```bash
chmod +x scripts/*.sh
./scripts/deploy-production.sh
```

Or manually:

```bash
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d --build
```

## Step 5 — Verify

```bash
curl http://localhost/health
# Expect: "status":"healthy", models gcn/gat/rf true

curl http://localhost/api/v1/metrics -H "Authorization: Bearer <token>"
```

Open in browser:
- **Dashboard:** `http://YOUR_SERVER_IP/`
- **Prevention:** `http://YOUR_SERVER_IP/prevention`
- **API docs:** `http://YOUR_SERVER_IP/docs`

Default login: `admin@gmail.com` / `Admin@12345` — **change immediately** in Settings.

## Step 6 — Enable HTTPS (recommended)

```bash
# Install certbot on host
sudo apt install certbot

# Stop nginx briefly, get cert (replace domain)
sudo certbot certonly --standalone -d your-domain.com

# Copy certs into project
sudo cp /etc/letsencrypt/live/your-domain.com/fullchain.pem deploy/certs/
sudo cp /etc/letsencrypt/live/your-domain.com/privkey.pem deploy/certs/
sudo chown $USER:$USER deploy/certs/*.pem

# Switch NGINX to TLS config
cp deploy/nginx.prod.tls.conf deploy/nginx.prod.conf

# Update .env URLs to https://
nano .env   # NEXT_PUBLIC_API_URL + CORS_ORIGINS

# Rebuild frontend with HTTPS URL and restart
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d --build
```

## Windows (Docker Desktop)

```powershell
.\scripts\deploy-production.ps1
```

Requires [Docker Desktop for Windows](https://docs.docker.com/desktop/setup/install/windows-install/).

## Operations

| Task | Command |
|------|---------|
| View logs | `docker compose -f docker-compose.yml -f docker-compose.prod.yml logs -f api` |
| Restart | `docker compose -f docker-compose.yml -f docker-compose.prod.yml restart` |
| Stop | `docker compose -f docker-compose.yml -f docker-compose.prod.yml down` |
| Update | `git pull && docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d --build` |
| Preflight | `./scripts/preflight-production.sh` |

## What runs where (production)

| Container | Role | Internal port |
|-----------|------|---------------|
| **nginx** | Public entry — routes `/` → frontend, `/api` + `/ws` → API | 80, 443 |
| **api** | GNN detection + prevention engine | 8000 |
| **frontend** | Next.js SOC dashboard | 3000 |
| **redis** | Prediction cache | 6379 |

Data persisted on host:
- `artifacts/backend/ddos.db` — alerts, mitigations, predictions
- `artifacts/models/` — ML weights (read-only mount)
- `redis_data` Docker volume — cache

## Cloud-specific notes

| Provider | Recommendation |
|----------|----------------|
| **AWS** | EC2 `t3.medium`, Security Group ports 80/443, Elastic IP |
| **Azure** | VM B2s, NSG allow 80/443 |
| **DigitalOcean** | Droplet 4GB, attach domain in DNS |
| **University lab** | Static IP VM, `./scripts/deploy-production.sh` |

Point your domain **A record** → server IP before enabling HTTPS.

See also [DEPLOYMENT.md](DEPLOYMENT.md) for architecture details and SOAR/webhook integration.
