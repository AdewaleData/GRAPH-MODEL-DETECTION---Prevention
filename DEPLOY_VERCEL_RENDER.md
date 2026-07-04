# Deploy Halal Graph — Vercel + Render (Step-by-Step)

Deploy the **dashboard on Vercel** and the **API + GNN + prevention on Render**.

Estimated time: **30–45 minutes** (first time).

---

## Before you start

You need:

- [ ] GitHub account
- [ ] [Render](https://render.com) account (free signup)
- [ ] [Vercel](https://vercel.com) account (free signup)
- [ ] ML models in `artifacts/models/` (`gcn_best.pt`, `gat_best.pt`, `rf_bundle.joblib`, etc.)

---

## Part 1 — Push code to GitHub

### Step 1: Create a GitHub repository

1. Go to [github.com/new](https://github.com/new)
2. Name it e.g. `Halal-Graph-Model`
3. **Do not** add README (you already have one)
4. Click **Create repository**

### Step 2: Push your project

Open PowerShell in your project folder:

```powershell
cd C:\Users\555555\OneDrive\Desktop\Halal-Graph-Model

git init
git add .
git status
```

Confirm `artifacts/models/` files are **included** (not ignored).

```powershell
git commit -m "Prepare for Vercel + Render deployment"
git branch -M main
git remote add origin https://github.com/YOUR_USERNAME/Halal-Graph-Model.git
git push -u origin main
```

Replace `YOUR_USERNAME` with your GitHub username.

---

## Part 2 — Deploy API on Render

### Step 3: Create Render web service

1. Go to [dashboard.render.com](https://dashboard.render.com)
2. Click **New +** → **Web Service**
3. Connect your **GitHub** account if prompted
4. Select repository **Halal-Graph-Model**
5. Configure:

| Field | Value |
|-------|--------|
| **Name** | `halal-graph-api` |
| **Region** | Choose closest to you (e.g. Frankfurt) |
| **Branch** | `main` |
| **Runtime** | **Docker** |
| **Root Directory** | *(leave empty — repo root)* |
| **Dockerfile Path** | `Dockerfile` |
| **Docker Context** | `.` |
| **Instance Type** | **Starter** ($7/mo) — recommended; free tier often fails with PyTorch |

### Step 4: Render environment variables

Scroll to **Environment Variables** and add:

| Key | Value |
|-----|--------|
| `JWT_SECRET` | Generate: run `openssl rand -hex 32` locally, or use Render’s random generator |
| `PRODUCTION` | `true` |
| `LIVE_SIMULATOR_ENABLED` | `true` |
| `MITIGATION_AUTO_ENABLED` | `true` |
| `MITIGATION_MODE` | `simulated` |
| `CORS_ORIGINS` | `https://placeholder.vercel.app` *(update after Vercel deploy)* |

### Step 5: Health check

| Field | Value |
|-------|--------|
| **Health Check Path** | `/health` |

### Step 6: Deploy

1. Click **Create Web Service**
2. Wait **10–20 minutes** (first Docker build installs PyTorch)
3. When status is **Live**, copy your URL, e.g.:

   `https://halal-graph-api.onrender.com`

### Step 7: Test API

Open in browser:

```
https://halal-graph-api.onrender.com/health
```

Expected JSON:

```json
{
  "status": "healthy",
  "models": { "gcn": true, "gat": true, "rf": true }
}
```

API docs: `https://halal-graph-api.onrender.com/docs`

---

## Part 3 — Deploy dashboard on Vercel

### Step 8: Import project

1. Go to [vercel.com/new](https://vercel.com/new)
2. **Import** your GitHub repo **Halal-Graph-Model**
3. Configure project:

| Field | Value |
|-------|--------|
| **Framework Preset** | Next.js |
| **Root Directory** | `frontend` ← click **Edit**, set to `frontend` |

### Step 9: Vercel environment variable

Add:

| Name | Value |
|------|--------|
| `BACKEND_URL` | `https://halal-graph-api.onrender.com` |
| `NEXT_PUBLIC_API_URL` | `https://halal-graph-api.onrender.com` |

Use **your** Render URL from Step 6. **No trailing slash.**  
`BACKEND_URL` powers the Vercel proxy (login works even if you forget `NEXT_PUBLIC_API_URL`).  
`NEXT_PUBLIC_API_URL` is still needed for **WebSockets** (live graph/alerts).

### Step 10: Deploy

1. Click **Deploy**
2. Wait **2–5 minutes**
3. Copy your Vercel URL, e.g.:

   `https://halal-graph-model.vercel.app`

### Step 11: Update CORS on Render

1. Back to **Render** → your `halal-graph-api` service → **Environment**
2. Edit `CORS_ORIGINS` to your **exact** Vercel URL:

   ```
   https://halal-graph-model.vercel.app
   ```

3. Save → Render will **redeploy** automatically

---

## Part 4 — Use the app

### Step 12: Login

1. Open your Vercel URL: `https://your-app.vercel.app`
2. Login:
   - **Email:** `admin@gmail.com`
   - **Password:** `Admin@12345`
3. **Change password** in Settings immediately

### Step 13: Pages to demo

| Page | URL |
|------|-----|
| Dashboard | `/dashboard` |
| Prevention | `/prevention` |
| Alerts | `/alerts` |
| Network graph | `/graph` |

### Step 14: Send test traffic (optional)

Use Render API docs → **POST** `/api/v1/predict` with a JWT token from login.

Or enable demo mode on Render temporarily:

```
LIVE_SIMULATOR_ENABLED=true
```

Redeploy → live simulated attack traffic will flow through the GNN.

---

## Quick reference

```
GitHub repo
    │
    ├── Render (Docker)     →  https://halal-graph-api.onrender.com
    │       FastAPI + GNN + prevention
    │
    └── Vercel (Next.js)    →  https://your-app.vercel.app
            Dashboard (talks to Render API)
```

---

## Troubleshooting

| Problem | Fix |
|---------|-----|
| Render build fails / out of memory | Use **Starter** plan, not Free |
| Vercel shows login but API errors | Check `NEXT_PUBLIC_API_URL` matches Render URL |
| CORS error in browser | Update `CORS_ORIGINS` on Render to exact Vercel URL |
| `/health` shows models false | Ensure `artifacts/models/*.pt` were pushed to GitHub |
| Render slow first request | Free/cold start — wait 30–60s or use Starter |
| WebSockets disconnect | Normal on free tier; pages still work via REST |

---

## Costs

| Service | Free tier | Recommended |
|---------|-----------|-------------|
| **Vercel** | Free for hobby | Free is fine |
| **Render** | Free (512 MB, sleeps) | **Starter ~$7/mo** for thesis demo |

---

## Alternative: Blueprint deploy on Render

If `render.yaml` is in your repo:

1. Render → **New +** → **Blueprint**
2. Connect repo → Render creates `halal-graph-api` from `render.yaml`
3. Set `CORS_ORIGINS` when prompted
4. Then deploy Vercel (Part 3)

---

## After thesis / defense

- Set `LIVE_SIMULATOR_ENABLED=false` on Render
- Rotate `JWT_SECRET` and admin password
- Consider Render **Postgres** if you need persistent alerts DB
