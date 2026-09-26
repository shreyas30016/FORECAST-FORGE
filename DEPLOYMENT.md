# Deployment Guide

## Backend Deployment (Railway)

### Prerequisites
- Railway account (https://railway.app)
- NVIDIA API key for NIM inference (https://build.nvidia.com)
- GitHub repository access

### Deployment Steps

1. **Connect Repository to Railway**
   - Log in to Railway dashboard
   - Click "New Project" → "Deploy from GitHub repo"
   - Select the `FORECAST-FORGE` repository

2. **Configure Environment Variables**
   Navigate to your service → Variables tab and add:

   | Variable | Value | Required | Description |
   |----------|-------|----------|-------------|
   | `NVIDIA_API_KEY` | `nvapi-xxxxx` | **YES** | NVIDIA NIM API key for ensemble inference |
   | `CORS_ALLOWED_ORIGINS` | `https://forecast-forge-ai.vercel.app,http://localhost:3000` | **YES** | Comma-separated allowed CORS origins |

   **Note:** Railway automatically detects the project as Python via `uv` or `pyproject.toml` and installs dependencies.

3. **Generate Domain**
   - Go to Settings → Networking
   - Click "Generate Domain"
   - Save the URL (e.g., `https://forecast-forge-production.up.railway.app`)

4. **Verify Deployment**
   Test endpoints:
   ```bash
   # Health check
   curl https://your-railway-domain.up.railway.app/api/v1/health
   
   # Forecast (Mumbai example)
   curl "https://your-railway-domain.up.railway.app/api/v1/forecast?latitude=19.0760&longitude=72.8777&horizon_hours=72&name=Mumbai"
   ```

---

## Frontend Deployment (Vercel)

### Prerequisites
- Vercel account (https://vercel.com)
- Deployed Railway backend URL
- GitHub repository access

### Deployment Steps

1. **Connect Repository to Vercel**
   - Log in to Vercel dashboard
   - Click "Add New Project"
   - Import the `FORECAST-FORGE` repository

2. **Configure Project Settings**
   - **Framework Preset**: `Next.js`
   - **Root Directory**: `ui`
   - Build Command, Output Directory, and Install Command will be auto-detected.

3. **Configure Environment Variables**
   In Project Settings → Environment Variables, add:

   | Variable | Value | Required | Description |
   |----------|-------|----------|-------------|
   | `NEXT_PUBLIC_API_BASE_URL` | `https://your-railway-domain.up.railway.app/api/v1` | **YES** | Backend API base URL (from Railway) |

4. **Deploy**
   - Click "Deploy"
   - First deployment takes ~2-3 minutes.

5. **Verify Deployment**
   Your frontend will be available at: `https://forecast-forge-ai.vercel.app`

---

## Security Notes

1. **Never commit `.env` files** - Use platform-specific secret management
2. **NVIDIA_API_KEY** - Keep this secret, rotate periodically
3. **CORS** - Keep `CORS_ALLOWED_ORIGINS` restricted to known domains
4. **HTTPS** - Both platforms enforce HTTPS by default
