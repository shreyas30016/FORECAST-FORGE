# Deployment Guide

## Backend Deployment (Render)

### Prerequisites
- Render account (https://render.com)
- NVIDIA API key for NIM inference (https://build.nvidia.com)
- GitHub repository access

### Deployment Steps

1. **Connect Repository to Render**
   - Log in to Render dashboard
   - Click "New +" → "Web Service"
   - Connect your GitHub account and select the `FORECAST-FORGE` repository
   - Render will auto-detect `render.yaml` configuration

2. **Configure Environment Variables**
   
   Navigate to your service → Environment tab and set:

   | Variable | Value | Required | Description |
   |----------|-------|----------|-------------|
   | `NVIDIA_API_KEY` | `nvapi-xxxxx` | **YES** | NVIDIA NIM API key for ensemble inference |
   | `PYTHON_VERSION` | `3.11.0` | Auto-set | Python runtime version |
   | `CORS_ALLOWED_ORIGINS` | `https://forecast-forge-ai.vercel.app,http://localhost:3000` | Auto-set | Comma-separated allowed CORS origins |
   | `LOG_LEVEL` | `INFO` | Auto-set | Logging verbosity (DEBUG, INFO, WARNING, ERROR) |

   **Critical**: `NVIDIA_API_KEY` must be set manually in the Render dashboard as it contains sensitive credentials.

3. **Deploy**
   - Click "Create Web Service"
   - Render will:
     - Install dependencies via `pip install -e .`
     - Start server with `uvicorn forecast_forge.api.app:app --host 0.0.0.0 --port $PORT`
     - Run health checks at `/api/v1/health`
   - First deployment takes ~5-10 minutes

4. **Verify Deployment**
   
   Once deployed, your backend will be available at:
   ```
   https://forecast-forge-api.onrender.com
   ```
   
   Test endpoints:
   ```bash
   # Health check
   curl https://forecast-forge-api.onrender.com/api/v1/health
   
   # Available models
   curl https://forecast-forge-api.onrender.com/api/v1/models
   
   # Forecast (Mumbai example)
   curl "https://forecast-forge-api.onrender.com/api/v1/forecast?latitude=19.0760&longitude=72.8777&horizon_hours=72&name=Mumbai"
   ```

### Backend URL
After deployment, note your backend URL (e.g., `https://forecast-forge-api.onrender.com`). You'll need this for Vercel configuration.

---

## Frontend Deployment (Vercel)

### Prerequisites
- Vercel account (https://vercel.com)
- Deployed Render backend URL
- GitHub repository access

### Deployment Steps

1. **Connect Repository to Vercel**
   - Log in to Vercel dashboard
   - Click "Add New Project"
   - Import the `FORECAST-FORGE` repository
   - Select the `ui` directory as the root

2. **Configure Environment Variables**
   
   In Project Settings → Environment Variables, add:

   | Variable | Value | Required | Description |
   |----------|-------|----------|-------------|
   | `NEXT_PUBLIC_API_BASE_URL` | `https://forecast-forge-api.onrender.com/api/v1` | **YES** | Backend API base URL (from Render deployment) |

   **Note**: The `NEXT_PUBLIC_` prefix makes this variable available in the browser.

3. **Configure Build Settings**
   - Framework Preset: `Next.js`
   - Root Directory: `ui`
   - Build Command: `npm run build` (auto-detected)
   - Output Directory: `.next` (auto-detected)
   - Install Command: `npm install` (auto-detected)

4. **Deploy**
   - Click "Deploy"
   - Vercel will:
     - Install dependencies
     - Build the Next.js application
     - Deploy to global CDN
   - First deployment takes ~2-3 minutes

5. **Verify Deployment**
   
   Your frontend will be available at:
   ```
   https://forecast-forge-ai.vercel.app
   ```
   
   Test in browser:
   - Visit the homepage
   - Enter Mumbai coordinates (19.0760, 72.8777)
   - Click "Get Forecast"
   - Verify all panels load (Forecast, Probabilistic, Bust Detection, Extremes)

---

## Development vs Production

### Local Development
```bash
# Backend (terminal 1)
cd forecast-forge-ai
uv sync
source .venv/bin/activate  # or `.venv\Scripts\activate` on Windows
uvicorn forecast_forge.api.app:app --reload --port 8000

# Frontend (terminal 2)
cd ui
npm install
npm run dev
```

Access at:
- Frontend: http://localhost:3000
- Backend API: http://localhost:8000
- API Docs: http://localhost:8000/docs

### Production
- Frontend: https://forecast-forge-ai.vercel.app
- Backend: https://forecast-forge-api.onrender.com
- API Docs: https://forecast-forge-api.onrender.com/docs

---

## Troubleshooting

### Backend Issues

**Build Fails**
- Verify `pyproject.toml` is valid
- Check Render build logs for missing dependencies
- Ensure Python 3.11 is specified

**Health Check Fails**
- Verify `/api/v1/health` endpoint returns `{"status":"OK"}`
- Check that uvicorn binds to `0.0.0.0` and uses `$PORT`
- Review Render logs for startup errors

**CORS Errors**
- Verify `CORS_ALLOWED_ORIGINS` includes your Vercel URL
- Check browser DevTools Console for specific CORS error
- Ensure no trailing slashes in origin URLs

**NVIDIA API Errors**
- Verify `NVIDIA_API_KEY` is set correctly in Render
- Test key validity at https://build.nvidia.com
- Check API usage quotas/limits

### Frontend Issues

**API Connection Fails**
- Verify `NEXT_PUBLIC_API_BASE_URL` is set in Vercel
- Check that URL includes `/api/v1` suffix
- Test backend URL directly with curl
- Inspect Network tab in browser DevTools

**Build Fails**
- Verify `ui/package.json` has all dependencies
- Check Vercel build logs for TypeScript errors
- Ensure Node.js version is compatible (18+)

**Environment Variable Not Applied**
- Redeploy after changing environment variables
- Verify variable name has `NEXT_PUBLIC_` prefix
- Check Production/Preview/Development scope

---

## Monitoring

### Render
- Logs: Service → Logs tab
- Metrics: Service → Metrics tab (CPU, Memory, Response Time)
- Events: Service → Events tab (Deploys, Crashes)

### Vercel
- Analytics: Project → Analytics (Performance, Web Vitals)
- Logs: Deployment → Function Logs
- Build Logs: Deployment → Build Logs

---

## Scaling Considerations

### Free Tier Limitations
- **Render Free**: Spins down after 15 min inactivity, cold start ~30s
- **Vercel Hobby**: 100 GB bandwidth/month, serverless function limits

### Recommendations for Production
- Upgrade Render to Starter ($7/mo) for always-on service
- Configure caching headers for static assets
- Monitor API usage to stay within NVIDIA quotas
- Use Vercel Analytics for performance insights

---

## Security Notes

1. **Never commit `.env` files** - Use platform-specific secret management
2. **NVIDIA_API_KEY** - Keep this secret, rotate periodically
3. **CORS** - Keep `CORS_ALLOWED_ORIGINS` restricted to known domains
4. **HTTPS** - Both platforms enforce HTTPS by default

---

## Support

- **Issues**: https://github.com/shreyas30016/FORECAST-FORGE/issues
- **Documentation**: See README.md for architecture details
- **Render Docs**: https://render.com/docs
- **Vercel Docs**: https://vercel.com/docs
