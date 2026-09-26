# Phase 6.6 — Public Backend Deployment + Remove All Localhost Dependencies

**Status**: Configuration Complete, Manual Deployment Required  
**Date**: 2026-09-25  
**Commit**: `07387d5`

---

## ✅ Completed Tasks

### 1. Localhost Reference Audit
**Status**: Complete

Found 7 localhost references across the codebase:

| File | Line | Type | Action Taken |
|------|------|------|--------------|
| `ui/next.config.ts` | 8 | Dev proxy | ✅ Acceptable (dev-only) |
| `ui/src/lib/api.ts` | 15 | Fallback URL | ✅ Updated to use `NEXT_PUBLIC_API_BASE_URL` |
| `ui/src/components/forecast/ProbabilisticPanel.tsx` | 24 | Direct fetch | ✅ Refactored to use `API_BASE_URL` export |
| `ui/src/components/forecast/ForecastBustPanel.tsx` | 42 | Direct fetch | ✅ Refactored to use `API_BASE_URL` export |
| `ui/src/components/forecast/ExtremesPanel.tsx` | 48 | Direct fetch | ✅ Refactored to use `API_BASE_URL` export |
| `forecast_forge/api/app.py` | 36 | CORS default | ✅ Updated to include Vercel URL |
| `README.md` | 235, 244 | Documentation | ✅ Acceptable (dev instructions) |

**Outcome**: All hardcoded localhost references eliminated from production code path.

---

### 2. Frontend API Configuration
**Status**: Complete

**Changes**:
- ✅ Renamed `NEXT_PUBLIC_API_URL` → `NEXT_PUBLIC_API_BASE_URL` (consistency)
- ✅ Exported `API_BASE_URL` constant from `ui/src/lib/api.ts`
- ✅ Updated 3 components to import centralized `API_BASE_URL`
- ✅ Maintained localhost fallback for local development

**Result**: Single source of truth for API base URL configuration.

---

### 3. Backend CORS Configuration
**Status**: Complete

**Changes**:
```python
# Before
"CORS_ALLOWED_ORIGINS", "http://localhost:3000,http://127.0.0.1:3000"

# After
"CORS_ALLOWED_ORIGINS", 
"http://localhost:3000,http://127.0.0.1:3000,https://forecast-forge-ai.vercel.app"
```

**Features**:
- ✅ Environment-driven via `CORS_ALLOWED_ORIGINS`
- ✅ Production Vercel URL included by default
- ✅ Localhost preserved for development
- ✅ Supports comma-separated multiple origins

---

### 4. Render Deployment Configuration
**Status**: Complete

**File**: `render.yaml`

```yaml
services:
  - type: web
    name: forecast-forge-api
    runtime: python
    plan: free
    region: oregon
    branch: main
    buildCommand: pip install -e .
    startCommand: uvicorn forecast_forge.api.app:app --host 0.0.0.0 --port $PORT
    envVars:
      - key: PYTHON_VERSION
        value: 3.11.0
      - key: NVIDIA_API_KEY
        sync: false
      - key: CORS_ALLOWED_ORIGINS
        value: https://forecast-forge-ai.vercel.app,http://localhost:3000
      - key: LOG_LEVEL
        value: INFO
    healthCheckPath: /api/v1/health
```

**Key Features**:
- ✅ Python 3.11 runtime
- ✅ Free tier deployment
- ✅ Oregon region (low latency for US)
- ✅ Automatic health checks at `/api/v1/health`
- ✅ Environment variables pre-configured
- ✅ `NVIDIA_API_KEY` marked as manual secret

---

### 5. Deployment Documentation
**Status**: Complete

**File**: `DEPLOYMENT.md` (232 lines)

**Sections**:
1. ✅ Backend Deployment (Render) — Complete walkthrough
2. ✅ Frontend Deployment (Vercel) — Step-by-step guide
3. ✅ Environment Variables — Full reference table
4. ✅ Development vs Production — URL comparison
5. ✅ Troubleshooting — Common issues + solutions
6. ✅ Monitoring — Render & Vercel observability
7. ✅ Scaling Considerations — Free tier limits
8. ✅ Security Notes — Best practices

---

### 6. Git Commit & Push
**Status**: Complete

**Commit**: `07387d5`  
**Message**: `feat: Phase 6.6 - Public deployment configuration`

**Files Changed**:
- `DEPLOYMENT.md` (new)
- `render.yaml` (new)
- `forecast_forge/api/app.py` (CORS update)
- `ui/src/lib/api.ts` (API_BASE_URL export)
- `ui/src/components/forecast/ProbabilisticPanel.tsx` (refactor)
- `ui/src/components/forecast/ForecastBustPanel.tsx` (refactor)
- `ui/src/components/forecast/ExtremesPanel.tsx` (refactor)

**Push Verification**: ✅ Successfully pushed to `origin/main`

---

## 🔲 Manual Deployment Steps Required

The following steps require manual dashboard access and cannot be automated:

### Task 8: Deploy Backend to Render

**Prerequisites**:
- Render account at https://render.com
- NVIDIA API key from https://build.nvidia.com
- GitHub repository access

**Steps**:

1. **Connect Repository**
   ```
   1. Log in to Render dashboard
   2. Click "New +" → "Web Service"
   3. Connect GitHub account
   4. Select repository: shreyas30016/FORECAST-FORGE
   5. Branch: main
   ```

2. **Configure Service**
   - Render will auto-detect `render.yaml`
   - Verify settings match the YAML configuration
   - Name: `forecast-forge-api`
   - Runtime: Python 3.11
   - Region: Oregon
   - Plan: Free

3. **Set NVIDIA_API_KEY**
   ```
   1. Navigate to service → Environment tab
   2. Add secret variable:
      Key: NVIDIA_API_KEY
      Value: nvapi-<your-actual-key>
   3. Click "Save Changes"
   ```

4. **Deploy**
   ```
   1. Click "Create Web Service"
   2. Wait for build (~5-10 minutes)
   3. Monitor logs for errors
   4. Wait for health check to pass
   ```

5. **Note Backend URL**
   ```
   Your backend will be available at:
   https://forecast-forge-api.onrender.com
   
   (Or different if the name was taken - note the actual URL)
   ```

**Expected Outcome**: Backend deployed and health check passing.

---

### Task 9: Configure Vercel Environment Variables

**Prerequisites**:
- Backend deployed to Render (Task 8 complete)
- Backend URL noted (e.g., `https://forecast-forge-api.onrender.com`)

**Steps**:

1. **Access Existing Vercel Project**
   ```
   1. Log in to Vercel dashboard
   2. Navigate to your existing project: forecast-forge-ai
   3. Click "Settings" → "Environment Variables"
   ```

2. **Add API Base URL**
   ```
   Variable Name: NEXT_PUBLIC_API_BASE_URL
   Value: https://forecast-forge-api.onrender.com/api/v1
   
   Important: Include the /api/v1 suffix!
   
   Apply to: Production, Preview, Development (all three)
   ```

3. **Save Configuration**
   ```
   1. Click "Save"
   2. Confirm the variable is visible in the list
   ```

**Expected Outcome**: Environment variable configured in Vercel.

---

### Task 10: Smoke Test Render Endpoints

**Prerequisites**:
- Backend deployed (Task 8 complete)
- Backend URL available

**Commands**:

```bash
# Set your backend URL
BACKEND_URL="https://forecast-forge-api.onrender.com"

# Test 1: Health Check
curl "${BACKEND_URL}/api/v1/health"
# Expected: {"status":"OK","version":"1.0.0","timestamp":"..."}

# Test 2: Available Models
curl "${BACKEND_URL}/api/v1/models"
# Expected: JSON array with model list (ecmwf_ifs025, gfs_0p25, etc.)

# Test 3: Forecast (Mumbai)
curl "${BACKEND_URL}/api/v1/forecast?latitude=19.0760&longitude=72.8777&horizon_hours=72&name=Mumbai"
# Expected: JSON with forecast data, ensemble members, weights

# Test 4: Data Sources Health
curl "${BACKEND_URL}/api/v1/data-sources/health"
# Expected: JSON array with provider health status
```

**Verification Checklist**:
- [ ] Health endpoint returns `200 OK`
- [ ] Models endpoint returns valid JSON array
- [ ] Forecast endpoint returns forecast data (may be slow on cold start)
- [ ] No CORS errors in responses
- [ ] Response times acceptable (<30s after cold start)

**Expected Outcome**: All endpoints responding correctly.

---

### Task 11: Redeploy Vercel Frontend

**Prerequisites**:
- Environment variable configured (Task 9 complete)
- Backend smoke tests passed (Task 10 complete)

**Steps**:

1. **Trigger Redeployment**
   ```
   1. Navigate to Vercel project: forecast-forge-ai
   2. Go to "Deployments" tab
   3. Click on latest deployment
   4. Click "..." menu → "Redeploy"
   5. Confirm "Redeploy"
   ```

2. **Monitor Build**
   ```
   1. Watch build logs in real-time
   2. Verify "Building" completes successfully
   3. Wait for "Deployment Ready" status
   4. Note the deployment URL (should be forecast-forge-ai.vercel.app)
   ```

3. **Check Environment Variable Injection**
   ```
   In build logs, search for:
   "Environment variables: NEXT_PUBLIC_API_BASE_URL"
   
   Verify it shows your backend URL.
   ```

**Expected Outcome**: Frontend redeployed with new API configuration.

---

### Task 12: Browser Integration Test

**Prerequisites**:
- Frontend redeployed (Task 11 complete)

**Test URL**: https://forecast-forge-ai.vercel.app

**Test Procedure**:

1. **Open DevTools**
   ```
   1. Open https://forecast-forge-ai.vercel.app
   2. Press F12 to open DevTools
   3. Go to "Network" tab
   4. Check "Preserve log"
   5. Filter: "Fetch/XHR"
   ```

2. **Test Mumbai Forecast**
   ```
   1. Click search icon
   2. Enter: Mumbai
   3. Select: Mumbai, Maharashtra, India
   4. Wait for forecast to load
   ```

3. **Verify Network Requests**
   ```
   Expected requests to: https://forecast-forge-api.onrender.com/api/v1/...
   
   Check:
   - [ ] /forecast request succeeds (200 OK)
   - [ ] /ensemble request succeeds (200 OK)
   - [ ] /probabilistic/* requests succeed (200 OK)
   - [ ] /bust/signal request succeeds (200 OK)
   - [ ] /extremes/guidance request succeeds (200 OK)
   - [ ] No CORS errors in Console
   - [ ] No localhost references in requests
   ```

4. **Visual Verification**
   ```
   Verify all panels display data:
   - [ ] Main Forecast Panel (temperature, precipitation, etc.)
   - [ ] Probabilistic Panel (distribution charts, event probabilities)
   - [ ] Forecast Bust Panel (bust signal, factors)
   - [ ] Extremes Panel (extreme event guidance)
   - [ ] Ensemble Weights (model weights displayed)
   ```

5. **Test Other Features**
   ```
   - [ ] Decision Provenance tab loads
   - [ ] Historical Evaluation tab loads
   - [ ] Temporal Replay tab loads
   - [ ] Settings (unit conversions) work
   - [ ] Dark mode toggle works
   ```

**Expected Outcome**: All features working with public backend, zero localhost references.

---

### Task 14: Validate All Frontend Features

**Extended Test Matrix**:

| Feature | Location | Test | Status |
|---------|----------|------|--------|
| Location Search | Sidebar | Mumbai, Delhi, New York | ⬜ |
| Forecast Panel | Main | Temperature, precipitation, wind | ⬜ |
| Probabilistic | Panel | Distribution, event probabilities | ⬜ |
| Forecast Bust | Panel | Signal, factors, regime | ⬜ |
| Extremes | Panel | Event list, thresholds | ⬜ |
| Ensemble Weights | Footer | Model weights per lead time | ⬜ |
| Decision Trace | Tab | Provenance tree, replay link | ⬜ |
| Historical Eval | Tab | CRPS, regime metrics | ⬜ |
| Temporal Replay | Tab | Timeline, state reconstruction | ⬜ |
| Settings | Menu | Celsius ↔ Fahrenheit, km/h ↔ mph | ⬜ |
| Dark Mode | Toggle | Theme persistence | ⬜ |
| Responsive | Mobile | Layout adapts | ⬜ |

**Performance Benchmarks**:
- Initial page load: <3s
- Forecast request: <5s (after backend warm-up)
- Panel rendering: <1s
- Navigation: <500ms

---

## 📊 Deployment Verification Checklist

Once manual tasks 8-12 are complete, verify:

### Backend (Render)
- [ ] Service status: Running
- [ ] Health check: Passing
- [ ] Logs: No errors
- [ ] Environment variables: All set (including NVIDIA_API_KEY)
- [ ] Endpoint accessibility: All `/api/v1/*` routes respond
- [ ] CORS headers: Include Vercel origin
- [ ] Python version: 3.11.x
- [ ] Response time: Acceptable (<30s after cold start)

### Frontend (Vercel)
- [ ] Deployment status: Ready
- [ ] Build: Successful
- [ ] Environment variable: `NEXT_PUBLIC_API_BASE_URL` set
- [ ] Production URL: https://forecast-forge-ai.vercel.app
- [ ] All features: Working
- [ ] Network requests: Point to Render backend
- [ ] No localhost references: Confirmed in DevTools
- [ ] CORS: No errors in Console

### Integration
- [ ] End-to-end forecast flow: Working
- [ ] All API endpoints: Reachable from frontend
- [ ] Data visualization: Rendering correctly
- [ ] Error handling: Graceful degradation
- [ ] Performance: Within acceptable limits

---

## 🎯 Success Criteria

**Phase 6.6 is complete when**:

1. ✅ All localhost dependencies removed from production code
2. ⬜ Backend deployed to Render with public URL
3. ⬜ Frontend deployed to Vercel with backend configured
4. ⬜ All smoke tests passing
5. ⬜ Full browser integration test passing
6. ⬜ No CORS errors
7. ⬜ No localhost references in Network tab
8. ⬜ All features operational from public URLs

**Demo-Ready State**:
- Public URL: https://forecast-forge-ai.vercel.app
- Backend API: https://forecast-forge-api.onrender.com
- Full functionality: All panels, provenance, replay
- SIH judges can access: No localhost dependency

---

## 📝 Post-Deployment Tasks

After successful deployment:

1. **Update README.md**
   - Add "Live Demo" section with public URL
   - Update deployment badges (if applicable)

2. **Create Demo Video**
   - Record screen capture of public deployment
   - Show all features working
   - Include URL in video

3. **Prepare SIH Presentation**
   - Live demo from public URL
   - Backup: Screenshots of all features
   - Emergency: Video walkthrough

4. **Monitor Initial Usage**
   - Check Render logs for errors
   - Monitor Vercel analytics for traffic
   - Verify NVIDIA API usage within quotas

5. **Document Known Issues**
   - Cold start latency (~30s on free tier)
   - Rate limits (if any)
   - Fallback procedures

---

## 🔧 Troubleshooting Reference

### Issue: Backend Not Building on Render
**Cause**: Missing dependencies or Python version mismatch  
**Solution**: Check `pyproject.toml`, verify Python 3.11 in render.yaml

### Issue: Health Check Failing
**Cause**: Port binding incorrect or startup crash  
**Solution**: Verify `--host 0.0.0.0 --port $PORT`, check startup logs

### Issue: CORS Errors in Browser
**Cause**: Vercel origin not in CORS_ALLOWED_ORIGINS  
**Solution**: Verify `CORS_ALLOWED_ORIGINS` includes `https://forecast-forge-ai.vercel.app`

### Issue: Frontend Still Uses Localhost
**Cause**: Environment variable not set or not redeployed  
**Solution**: Verify `NEXT_PUBLIC_API_BASE_URL` in Vercel settings, trigger redeploy

### Issue: NVIDIA API Errors
**Cause**: Invalid key or quota exceeded  
**Solution**: Verify key at https://build.nvidia.com, check usage limits

### Issue: Slow Response Times
**Cause**: Free tier cold start or NVIDIA API latency  
**Solution**: Expected on free tier (<30s), consider paid tier for always-on

---

## 📌 Configuration Summary

### Environment Variables (Render)
```
PYTHON_VERSION=3.11.0
NVIDIA_API_KEY=nvapi-<your-key>  # MUST BE SET MANUALLY
CORS_ALLOWED_ORIGINS=https://forecast-forge-ai.vercel.app,http://localhost:3000
LOG_LEVEL=INFO
```

### Environment Variables (Vercel)
```
NEXT_PUBLIC_API_BASE_URL=https://forecast-forge-api.onrender.com/api/v1
```

### URLs
- **Frontend (Production)**: https://forecast-forge-ai.vercel.app
- **Backend (Production)**: https://forecast-forge-api.onrender.com
- **API Docs**: https://forecast-forge-api.onrender.com/docs
- **Health Check**: https://forecast-forge-api.onrender.com/api/v1/health

---

## ✨ Summary

**Configuration Phase**: ✅ Complete  
**Manual Deployment Phase**: 🔲 Pending (Tasks 8-12)  
**Verification Phase**: 🔲 Pending (Tasks 13-14)  

**Next Steps**:
1. Follow Task 8 to deploy backend to Render
2. Follow Task 9 to configure Vercel environment
3. Follow Task 10 to smoke test backend
4. Follow Task 11 to redeploy frontend
5. Follow Task 12 to browser integration test
6. Complete Task 14 validation matrix
7. Mark Phase 6.6 as complete

**Commit**: `07387d5`  
**Branch**: `main`  
**Status**: Ready for deployment

---

**End of Phase 6.6 Audit**
