# Deployment Guide: Render (Backend) + Vercel (Frontend)

## Prerequisites
- GitHub account
- Render account (free tier)
- Vercel account (free tier)
- API keys for LLM providers (OpenAI, Anthropic, Google Gemini)

---

## 1. Deploy Backend to Render

### Option A: Using render.yaml (Recommended)
1. Push your code to GitHub
2. Go to [Render Dashboard](https://dashboard.render.com)
3. Click **New** → **Blueprint**
4. Connect your GitHub repo
5. Render will detect `render.yaml` and configure everything
6. Click **Apply**

### Option B: Manual Setup
1. Go to [Render Dashboard](https://dashboard.render.com)
2. Click **New** → **Web Service**
3. Connect your GitHub repo
4. Configure:
   - **Name**: `iq-math-backend`
   - **Environment**: `Python 3`
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `uvicorn main:app --host 0.0.0.0 --port $PORT`
   - **Plan**: Free

### Environment Variables (Required)
Add these in Render Dashboard → Environment:
```
ALLOWED_ORIGINS=https://your-vercel-app.vercel.app
# Optional: Add LLM API keys if you want to pre-configure
# OPENAI_API_KEY=sk-...
# ANTHROPIC_API_KEY=sk-...
# GOOGLE_API_KEY=...
```

### Database Note
The app uses SQLite (`agent_runs.sqlite3`). On Render's free tier:
- The database file persists across deploys but **not across instance restarts** (free tier spins down after 15 min inactivity)
- For production, consider PostgreSQL (Render offers free PostgreSQL)

---

## 2. Deploy Frontend to Vercel

### Via Vercel Dashboard
1. Go to [Vercel Dashboard](https://vercel.com/dashboard)
2. Click **Add New** → **Project**
3. Import your GitHub repo
4. Select `iq-math-technologies-frontend` as root directory
5. Configure:
   - **Framework Preset**: Vite
   - **Build Command**: `npm run build`
   - **Output Directory**: `dist`
6. Add Environment Variable:
   ```
   VITE_AGENT_API_URL=https://your-render-backend.onrender.com
   ```
7. Click **Deploy**

### Via Vercel CLI
```bash
cd iq-math-technologies-frontend
npm i -g vercel
vercel
# Follow prompts, set root directory to iq-math-technologies-frontend
vercel env add VITE_AGENT_API_URL
# Enter: https://your-render-backend.onrender.com
vercel --prod
```

---

## 3. Connect Both

1. **Get your Render URL**: After deploy, copy the URL (e.g., `https://iq-math-backend.onrender.com`)
2. **Update Vercel**: Add/update `VITE_AGENT_API_URL` in Vercel project settings
3. **Update Render**: Add your Vercel URL to `ALLOWED_ORIGINS` in Render environment variables
4. **Redeploy both** to pick up changes

---

## 4. Test the Deployment

1. Visit your Vercel URL
2. Click "AI AGENT SHOWCASE" section
3. Click "AI Providers" button
4. Enter your LLM API key (OpenAI/Anthropic/Gemini)
5. Select an agent and run it

---

## 5. Free Tier Limitations

| Platform | Limitation |
|----------|------------|
| Render | Spins down after 15 min inactivity (cold start ~30-60s) |
| Render | 512 MB RAM, shared CPU |
| Render | SQLite not persistent across restarts |
| Vercel | 100 GB bandwidth/month |
| Vercel | Serverless functions: 10s timeout (not used here) |

---

## 6. Troubleshooting

### Backend not starting?
- Check Render logs for missing dependencies
- Ensure `requirements.txt` has all packages

### WebSocket connection fails?
- Verify `VITE_AGENT_API_URL` uses `https://`
- Check Render logs for CORS errors
- Ensure `ALLOWED_ORIGINS` includes your Vercel URL

### CORS errors?
- Update `ALLOWED_ORIGINS` in Render to include your exact Vercel URL
- Redeploy backend after changes

### Agent execution fails?
- Check Render logs for LLM API errors
- Verify API keys are valid
- Free tier may hit rate limits

---

## 7. Custom Domains (Optional)

**Vercel**: Project Settings → Domains → Add
**Render**: Service Settings → Custom Domains → Add

Update `ALLOWED_ORIGINS` and `VITE_AGENT_API_URL` accordingly.