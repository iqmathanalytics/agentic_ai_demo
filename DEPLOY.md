# Deployment Guide — Nexperts Academy AI Agent Workspace

Repo: https://github.com/iqmathanalytics/agentic_ai_demo

---

## Part 1 — Backend on Render

### 1. Create the Web Service

1. Go to https://render.com → **New → Web Service**
2. Connect the `iqmathanalytics/agentic_ai_demo` repository
3. Fill in:

| Setting | Value |
|---|---|
| Name | `nexperts-academy-backend` |
| Root Directory | `backend` |
| Environment | `Python 3` |
| Build Command | `pip install -r requirements.txt` |
| Start Command | `uvicorn app.main:app --host 0.0.0.0 --port $PORT` |
| Plan | Free (or Starter) |

### 2. Set Environment Variables

In **Render → Service → Environment**, add:

| Key | Value |
|---|---|
| `ALLOWED_ORIGINS` | `https://nexperts-academy.pages.dev,https://www.nexpertsai.com` *(update after Cloudflare deploy)* |
| `ALPHA_VANTAGE_KEY` | your key |
| `FINNHUB_KEY` | your key |
| `FMP_KEY` | your key |
| `TAVILY_API_KEY` | your key |
| `SERPER_API_KEY` | your key |

> Users enter their own OpenAI / Groq / Google keys in the UI, so those do not need to be set server-side unless you want server-side defaults.

### 3. Deploy

Click **Create Web Service**. Render will build and deploy automatically.

Note your backend URL — it will look like:
```
https://nexperts-academy-backend.onrender.com
```

### 4. Health check

Visit `https://nexperts-academy-backend.onrender.com/health` — you should see:
```json
{"status": "ok"}
```

---

## Part 2 — Frontend on Cloudflare Pages

### 1. Create the Pages Project

1. Go to https://dash.cloudflare.com → **Workers & Pages → Create → Pages → Connect to Git**
2. Connect the `iqmathanalytics/agentic_ai_demo` repository
3. Fill in:

| Setting | Value |
|---|---|
| Project name | `nexperts-academy` |
| Production branch | `master` |
| Root directory | `iq-math-technologies-frontend` |
| Framework preset | `Vite` |
| Build command | `npm install && npm run build` |
| Build output directory | `dist` |

### 2. Set Environment Variables

In **Settings → Environment variables → Production**, add:

| Key | Value |
|---|---|
| `VITE_AGENT_API_URL` | `https://nexperts-academy-backend.onrender.com` |

> Important: the variable name must start with `VITE_` so Vite includes it in the bundle.

### 3. Deploy

Click **Save and Deploy**. Cloudflare will build and push to its CDN.

Your frontend URL will be:
```
https://nexperts-academy.pages.dev
```
(Or your custom domain if you add one in Pages → Custom domains)

### 4. Update Render CORS

Go back to Render → `nexperts-academy-backend` → Environment, and update `ALLOWED_ORIGINS` to include the real Pages URL:
```
https://nexperts-academy.pages.dev,https://www.nexpertsai.com,http://localhost:5173
```
Then **Manual Deploy → Clear cache and deploy** to apply the change.

---

## Part 3 — Custom Domain (optional)

If you want `app.nexpertsai.com` or similar:

1. Cloudflare Pages → Custom domains → add your domain
2. Since your domain is already on Cloudflare, the CNAME will be added automatically

---

## Summary of URLs (current production)

| Component | URL |
|---|---|
| Frontend | https://agentic-ai-demo.pages.dev |
| Backend | https://nexpertsagenticai.onrender.com |
| Backend health | https://nexpertsagenticai.onrender.com/health |
| WebSocket | wss://nexpertsagenticai.onrender.com/ws/agent |

---

## Stock agent — required Render environment variables

Yahoo Finance is often **blocked on cloud servers** (Render). The stock agent falls back to **Financial Modeling Prep (FMP)** for full fundamentals, charts, and analyst data.

**You must set these in Render → Environment** (empty values = 25% data completeness):

| Key | Required for |
|---|---|
| `FMP_KEY` | Price, market cap, PE, fundamentals, valuation, risk, chart (primary cloud fallback) |
| `TAVILY_API_KEY` | Company profile + news search |
| `SERPER_API_KEY` | Company profile + news search (merged with Tavily) |
| `ALPHA_VANTAGE_KEY` | Backup price history (especially Indian NSE stocks) |
| `FINNHUB_KEY` | Backup real-time quotes |

After adding keys, click **Manual Deploy** on Render to restart with the new values.

Cloudflare must have:
```
VITE_AGENT_API_URL=https://nexpertsagenticai.onrender.com
```
Then trigger a **new Pages deployment** so the frontend bundle picks up the backend URL.

---

## Free-tier caveats

- **Render free plan:** the service spins down after 15 minutes of inactivity; the first request after sleep takes ~30 s.
  - Upgrade to Render **Starter ($7/mo)** to avoid this.
- **Cloudflare Pages:** unlimited free static hosting — no caveats.
