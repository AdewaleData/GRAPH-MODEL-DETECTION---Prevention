# Halal Graph — Frontend Dashboard

Enterprise-style Next.js dashboard for real-time DDoS detection (Graph Neural Networks).

## Stack

- Next.js 14 (App Router) + TypeScript
- Tailwind CSS (dark cybersecurity theme)
- Recharts (analytics)
- Cytoscape.js (network graph)
- Zustand (auth + realtime state)
- WebSockets → FastAPI backend

## Quick start

1. Start the backend (`backend/run_server.ps1`) on port **8000**
2. Install and run the dashboard:

```bash
cd frontend
pnpm install
pnpm dev
```

3. Open [http://localhost:3000](http://localhost:3000)
4. Sign in: `admin@gmail.com` / `Admin@12345`

## Pages

| Route | Purpose |
|-------|---------|
| `/dashboard` | Overview, metrics, mini graph |
| `/traffic` | Live traffic stream |
| `/alerts` | Security alerts |
| `/graph` | Full Cytoscape network graph |
| `/analytics` | Model benchmarks & confusion matrices |
| `/health` | API & WebSocket status |
| `/settings` | Account & API URL |
| `/login`, `/register` | Authentication |

## Architecture

```
src/
├── app/              # Routes (auth + dashboard groups)
├── components/       # UI, layout, charts, graph
├── hooks/            # useWebSockets
├── lib/              # api client, config, utils
├── store/            # zustand (auth, realtime)
└── types/            # API TypeScript types
```

API base URL is hardcoded in `src/lib/config.ts` (`http://127.0.0.1:8000`).

## Deployment

- **Vercel**: `pnpm build` — set backend CORS to include your domain
- **Docker**: multi-stage build with `node:20-alpine`, expose 3000
- Run backend separately; frontend is static/SSR only

## Demo tips

- Run predictions via API or notebook to populate traffic/alerts
- Graph page: enter a victim IP from `/api/v1/graph/victims`
- WebSocket indicators on sidebar & health page show live feeds
