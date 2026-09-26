# Simplest Deployment (5 Minutes)

## Problem
Vercel monorepo with Python backend is complex. Let's use a simpler approach.

## Solution: Frontend (Vercel) + Backend (Railway)

### Why Railway Instead of Render?
- ✅ **No cold starts** (always on, even on free tier)
- ✅ **Faster deployment** (~2 min vs 5-10 min)
- ✅ **Better free tier** (500 hours/month)
- ✅ **Simpler than Render**
- ✅ **Automatic deployments** from GitHub

---

## 🚀 Deploy Backend to Railway (2 minutes)

1. Go to https://railway.app
2. Sign in with GitHub
3. Click **"New Project"**
4. Click **"Deploy from GitHub repo"**
5. Select: `shreyas30016/FORECAST-FORGE`
6. Railway auto-detects Python ✅
7. Click **"Deploy"**
8. Add environment variables:
   - Click **"Variables"** tab
   - Add: `NVIDIA_API_KEY = nvapi-<your-key>`
   - Add: `CORS_ALLOWED_ORIGINS = https://forecast-forge-ai.vercel.app`
9. Wait 2 minutes for deployment
10. Copy your Railway URL (e.g., `https://forecast-forge-production.up.railway.app`)

---

## 🎨 Configure Frontend on Vercel (1 minute)

1. Go to your Vercel dashboard
2. Select your project: `forecast-forge-ai`
3. Go to **Settings** → **General**
4. Set **Root Directory**: `ui`
5. Set **Framework Preset**: Next.js
6. Go to **Settings** → **Environment Variables**
7. Update or add:
   ```
   NEXT_PUBLIC_API_BASE_URL = https://your-railway-url.up.railway.app/api/v1
   ```
8. Click **Deployments** → Latest → **Redeploy**

---

## ✅ Verify

After 3 minutes total:

**Backend (Railway)**:
```bash
curl https://your-railway-url.up.railway.app/api/v1/health
```

**Frontend (Vercel)**:
```
https://forecast-forge-ai.vercel.app
```

Open DevTools → Network tab and verify requests go to Railway URL.

---

## 📊 Comparison

| Feature | Render | Railway | Vercel Python |
|---------|--------|---------|---------------|
| Cold start | ~30s | None | ~5s |
| Free tier hours | 750/month | 500/month | Limited |
| Setup complexity | Medium | Easy | Hard (monorepo) |
| Auto-deploy | ✅ | ✅ | ❌ |
| Always on (free) | ❌ | ✅ | ❌ |

**Winner**: Railway for backend + Vercel for frontend! 🏆

---

## Alternative: Use Render (Original Plan)

If you prefer Render, follow `DEPLOYMENT.md` instead. Both work great!

The monorepo Vercel approach (`vercel.json` with Python) is too complex for quick deployment.
