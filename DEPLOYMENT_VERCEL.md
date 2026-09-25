# Vercel-Only Deployment Guide

This guide covers deploying **both frontend and backend** to Vercel in a single unified deployment.

## Architecture

```
forecast-forge-ai.vercel.app/
├── /                    → Next.js Frontend (ui/)
├── /api/v1/*           → FastAPI Backend (via serverless functions)
└── /docs               → API Documentation (FastAPI auto-generated)
```

**Advantages of Vercel-Only Deployment:**
- ✅ Single platform, single deployment
- ✅ Shared domain (no CORS issues)
- ✅ Automatic HTTPS
- ✅ Global CDN for both frontend and API
- ✅ Simplified configuration
- ✅ Free tier includes both frontend + backend

---

## Prerequisites

- Vercel account (https://vercel.com)
- NVIDIA API key (https://build.nvidia.com)
- GitHub repository: `shreyas30016/FORECAST-FORGE`

---

## Deployment Steps

### 1. Connect Repository to Vercel

1. Log in to Vercel dashboard
2. Click **"Add New Project"**
3. Import repository: `shreyas30016/FORECAST-FORGE`
4. Vercel will detect both Next.js (ui/) and Python API (api/)

### 2. Configure Build Settings

Vercel will auto-detect settings from `vercel.json`, but verify:

- **Framework Preset**: Next.js
- **Root Directory**: (leave empty - monorepo)
- **Build Command**: Auto-detected
- **Output Directory**: Auto-detected
- **Install Command**: Auto-detected

### 3. Configure Environment Variables

In Project Settings → Environment Variables, add:

| Variable | Value | Scope | Required |
|----------|-------|-------|----------|
| `NVIDIA_API_KEY` | `nvapi-xxxxx` | Production, Preview, Development | **YES** |
| `PYTHON_VERSION` | `3.11` | Production, Preview, Development | **YES** |
| `CORS_ALLOWED_ORIGINS` | `https://forecast-forge-ai.vercel.app,http://localhost:3000` | Production, Preview | No (has default) |

**Critical**: Store `NVIDIA_API_KEY` as a **secret** (toggle the "Secret" option).

### 4. Deploy

1. Click **"Deploy"**
2. Vercel will:
   - Build Next.js frontend
   - Package Python API as serverless functions
   - Deploy both to global CDN
3. First deployment: ~3-5 minutes

### 5. Verify Deployment

Your application will be live at:
```
https://forecast-forge-ai.vercel.app
```

**Test Backend Endpoints**:
```bash
# Health check
curl https://forecast-forge-ai.vercel.app/api/v1/health

# Models
curl https://forecast-forge-ai.vercel.app/api/v1/models

# Forecast (Mumbai)
curl "https://forecast-forge-ai.vercel.app/api/v1/forecast?latitude=19.0760&longitude=72.8777&horizon_hours=72&name=Mumbai"
```

**Test Frontend**:
1. Visit https://forecast-forge-ai.vercel.app
2. Search for "Mumbai"
3. Verify all panels load with data

---

## Configuration Files

### `vercel.json`
```json
{
  "version": 2,
  "builds": [
    {
      "src": "ui/package.json",
      "use": "@vercel/next"
    },
    {
      "src": "api/index.py",
      "use": "@vercel/python"
    }
  ],
  "routes": [
    {
      "src": "/api/v1/(.*)",
      "dest": "/api/index.py"
    },
    {
      "src": "/(.*)",
      "dest": "/ui/$1"
    }
  ]
}
```

### `api/index.py`
Entry point for Python serverless functions:
```python
from mangum import Mangum
from forecast_forge.api.app import app

handler = Mangum(app, lifespan="off")
```

### `requirements.txt`
Python dependencies for backend:
```
fastapi>=0.141.1
httpx>=0.27.0
openai>=3.19.2
pandas>=3.0.6
pyarrow>=25.0.1
pydantic>=2.7.0
pydantic-settings>=2.2.0
scikit-learn>=1.9.1
uvicorn>=0.53.0
mangum>=0.17.0
```

---

## Local Development

### Backend
```bash
cd forecast-forge-ai
uv sync
.venv\Scripts\activate  # Windows
uvicorn forecast_forge.api.app:app --reload --port 8000
```

Access at: http://localhost:8000/docs

### Frontend
```bash
cd ui
npm install
npm run dev
```

Access at: http://localhost:3000

**Note**: In development, frontend calls `localhost:8000` backend. In production, frontend calls `/api/v1` (same domain).

---

## Environment Variables

### Development (.env.local in ui/)
```bash
# Optional: Override API URL in development
# NEXT_PUBLIC_API_BASE_URL=http://localhost:8000/api/v1
```

### Production (Vercel Dashboard)
```bash
NVIDIA_API_KEY=nvapi-xxxxx  # REQUIRED - Set as secret
PYTHON_VERSION=3.11
CORS_ALLOWED_ORIGINS=https://forecast-forge-ai.vercel.app
```

---

## Advantages vs. Render + Vercel

| Feature | Render + Vercel | Vercel Only |
|---------|----------------|-------------|
| Number of platforms | 2 | 1 |
| CORS complexity | High (cross-origin) | Low (same origin) |
| Configuration files | 2 (render.yaml + config) | 1 (vercel.json) |
| Cold start | ~30s (Render free tier) | ~5s (serverless) |
| Deployment time | ~10 min total | ~5 min total |
| Free tier limits | Render sleeps after 15 min | Always available |
| Environment variables | Set in 2 places | Set in 1 place |
| Monitoring | 2 dashboards | 1 dashboard |

---

## Limitations

### Vercel Serverless Constraints

1. **Execution Time**: 10s max (Hobby), 60s max (Pro)
   - Most API calls complete in <5s
   - NVIDIA inference typically <3s
   - Historical queries may timeout on Hobby tier

2. **Memory**: 1024 MB max (Hobby), 3008 MB max (Pro)
   - Pandas/PyArrow operations fit comfortably
   - Model ensemble fits in memory

3. **Cold Start**: ~2-5s first request
   - Much faster than Render free tier (~30s)
   - Warm functions respond instantly

4. **Bundle Size**: 250 MB max (including dependencies)
   - Current dependencies: ~150 MB
   - Well within limits

### Recommendations

- ✅ **For SIH Demo**: Vercel-only is ideal (simpler, faster cold start)
- ✅ **For Production**: Vercel-only works great on Pro tier
- ⚠️ **For Heavy Computation**: Consider Render if you need >60s execution time

---

## Troubleshooting

### Issue: API 404 on Vercel

**Symptom**: `/api/v1/*` routes return 404

**Solution**: 
1. Verify `api/index.py` exists
2. Check `vercel.json` routes configuration
3. Ensure `requirements.txt` includes `mangum`
4. Redeploy

### Issue: Module Not Found

**Symptom**: `ModuleNotFoundError: No module named 'forecast_forge'`

**Solution**:
1. Ensure `forecast_forge/` directory is in root
2. Check `requirements.txt` doesn't include `-e .` (not supported by Vercel)
3. Verify all imports use absolute paths: `from forecast_forge.api...`

### Issue: NVIDIA API Timeout

**Symptom**: API returns 504 Gateway Timeout

**Solution**:
1. Upgrade to Vercel Pro (60s timeout instead of 10s)
2. Or reduce ensemble size / horizon hours
3. Or add caching layer

### Issue: Cold Start Too Slow

**Symptom**: First request takes >5s

**Solution**:
1. Expected behavior for serverless
2. Subsequent requests are fast (<500ms)
3. Use Vercel Pro "Edge Functions" for faster cold starts
4. Or add a warming function (call API every 5 min)

---

## Monitoring

### Vercel Dashboard

- **Analytics**: Real-time traffic, latency, errors
- **Logs**: Function execution logs, errors, stdout
- **Insights**: Performance metrics per route
- **Usage**: Bandwidth, function invocations, build minutes

### Key Metrics

- API response time: <2s (p95)
- Frontend load time: <3s
- Function cold start: <5s
- Forecast generation: <3s (after cold start)

---

## Scaling

### Free Tier (Hobby)

- 100 GB bandwidth/month
- 100,000 function invocations/day
- 100 hours serverless execution/month
- Sufficient for SIH demo + moderate usage

### Pro Tier ($20/month)

- 1 TB bandwidth/month
- 1,000,000 function invocations/day
- 1,000 hours serverless execution/month
- 60s function timeout (vs. 10s)
- Priority support

---

## Security

1. **NVIDIA_API_KEY**: Always store as secret in Vercel
2. **CORS**: Keep `CORS_ALLOWED_ORIGINS` restricted
3. **HTTPS**: Enforced automatically by Vercel
4. **Environment Isolation**: Production/Preview/Development separated

---

## Next Steps

After successful deployment:

1. **Test All Features**: Verify every panel, tab, and interaction
2. **Monitor Usage**: Check Vercel Analytics for errors
3. **Optimize Performance**: Review slow endpoints
4. **Document Public URL**: Add to README.md
5. **Prepare Demo**: Test from different networks/devices

---

## Quick Reference

**Production URL**: https://forecast-forge-ai.vercel.app  
**API Docs**: https://forecast-forge-ai.vercel.app/docs  
**Health Check**: https://forecast-forge-ai.vercel.app/api/v1/health  
**Dashboard**: https://vercel.com/dashboard  
**Support**: https://vercel.com/docs

---

**End of Vercel Deployment Guide**
