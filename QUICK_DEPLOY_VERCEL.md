# 🚀 Quick Deploy to Vercel (5 Minutes)

## One-Platform Deployment: Frontend + Backend Together

Your repository is now configured for **unified Vercel deployment** - both Next.js frontend and FastAPI backend on the same platform!

---

## ⚡ Deploy Now (3 Steps)

### Step 1: Import to Vercel (2 min)

1. Go to https://vercel.com
2. Click **"Add New Project"**
3. Import: `shreyas30016/FORECAST-FORGE`
4. Click **"Deploy"** (Vercel auto-detects everything from `vercel.json`)

### Step 2: Add NVIDIA API Key (1 min)

1. While deploying, go to **Settings** → **Environment Variables**
2. Add:
   ```
   Name: NVIDIA_API_KEY
   Value: nvapi-<your-key>
   Toggle: Secret ✅
   Apply to: Production, Preview, Development
   ```
3. Click **Save**

### Step 3: Redeploy (2 min)

1. Go to **Deployments** tab
2. Click latest deployment → **"Redeploy"**
3. Wait for completion (~3 minutes)

---

## ✅ That's It!

Your app is now live at:
```
https://forecast-forge-ai.vercel.app
```

**Test it:**
```bash
# Backend health
curl https://forecast-forge-ai.vercel.app/api/v1/health

# Frontend
open https://forecast-forge-ai.vercel.app
```

---

## 📋 What Changed from Render Approach

| Aspect | Render + Vercel (Old) | Vercel Only (New) |
|--------|----------------------|-------------------|
| **Platforms** | 2 separate | 1 unified |
| **Setup time** | ~15 min | ~5 min |
| **Config files** | render.yaml + vercel config | vercel.json only |
| **URLs** | 2 different domains | 1 shared domain |
| **CORS** | Complex (cross-origin) | Simple (same-origin) |
| **Cold start** | ~30s (Render free) | ~5s (Vercel serverless) |
| **Env vars** | Set in 2 places | Set in 1 place |
| **Cost** | Free + Free | Free |

**Winner**: Vercel-only is simpler, faster, and easier to manage! ✨

---

## 🔧 New Files Added

- ✅ `vercel.json` - Deployment configuration (frontend + backend routing)
- ✅ `api/index.py` - Serverless entry point for FastAPI
- ✅ `requirements.txt` - Python dependencies
- ✅ `DEPLOYMENT_VERCEL.md` - Complete deployment guide

## 📝 Files Modified

- ✅ `ui/src/lib/api.ts` - Uses relative path `/api/v1` in production
- ✅ `forecast_forge/api/app.py` - Updated CORS for same-origin

---

## 🎯 Why This Is Better

1. **Single Platform** - Everything in one Vercel dashboard
2. **Faster Cold Start** - 5s vs. 30s on Render free tier
3. **No CORS Issues** - Same domain = no cross-origin complexity
4. **Simpler Config** - One file (`vercel.json`) vs. multiple
5. **Always Available** - Vercel free tier doesn't sleep like Render
6. **Better for SIH Demo** - More reliable, faster response times

---

## 📚 Full Documentation

- **Quick Start**: This file (QUICK_DEPLOY_VERCEL.md)
- **Complete Guide**: DEPLOYMENT_VERCEL.md
- **Original Render Guide**: DEPLOYMENT.md (if you prefer Render)

---

## 🆘 Troubleshooting

**Issue**: API returns 404
- **Fix**: Check `api/index.py` exists, redeploy

**Issue**: Module not found
- **Fix**: Ensure `forecast_forge/` is in repo root

**Issue**: NVIDIA API timeout
- **Fix**: Upgrade to Vercel Pro ($20/mo) for 60s timeout

**Issue**: Cold start slow
- **Fix**: Expected for first request (~5s), then fast

---

## 🎉 You're Done!

Your full-stack weather forecasting app is now deployed with:
- ✅ Frontend: Next.js 16
- ✅ Backend: FastAPI + Python 3.11
- ✅ API: Serverless functions
- ✅ Everything on one domain

**Demo URL**: https://forecast-forge-ai.vercel.app

Share it with SIH judges! 🏆
