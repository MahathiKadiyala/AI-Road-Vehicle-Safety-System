# Production Deployment & Operations Checklist

Comprehensive deployment runbook and operational checklist for the **AI-Powered Road and Vehicle Safety System (`AI-Road-Vehicle-Safety-System`)**.

---

## 1. Safety & Deployment Principles

1. **Zero Mock AI Claims:** Unweighted models (`road_damage_yolo.pt` or `accident_risk_xgb.json`) must report honest `503 SERVICE_UNAVAILABLE` states. Never simulate, mock, or fabricate neural network predictions or accident risk scores in production.
2. **Statutory Integrity:** Vehicle compliance assessments evaluate against authoritative Indian standards (CMVR 1989 Rule 95 / AIS-044). Assessments are preliminary engineering evaluations and must always display the mandatory statutory disclaimer.
3. **Emergency Proximity Disclaimer:** Hospital distances are straight-line geometric approximations for emergency situational awareness. Never present straight-line calculations as real-time road driving navigation or ambulance ETA. Emergency dispatch numbers (112, 108, 100, 103) must remain prominent.
4. **Zero Secret Leaks:** Never commit `.env` files, production credentials, or real personal data. All diagnostics and logs must sanitize database passwords.

---

## 2. Pre-Deployment Verification Checklist

Before deploying any build to staging or production, run the automated verification pipeline:

```powershell
# 1. Backend test suite (166+ unit, integration, and security tests)
& backend\venv\Scripts\python.exe -m pytest backend/tests -v

# 2. Frontend production compilation and typecheck
npm --prefix frontend run build

# 3. Git hygiene and secret inspection
git status --short
git diff --check

# 4. Confirm no untracked secrets, weights, or datasets exist
git status --ignored
```

---

## 3. Production Environment Configuration

### Backend Environment Variables (`backend/.env`)

| Variable | Type | Example Production Value | Purpose & Security Note |
| :--- | :--- | :--- | :--- |
| `PROJECT_NAME` | string | `AI-Powered Road and Vehicle Safety System` | Project identification header |
| `ENVIRONMENT` | string | `production` | Disables debug stack traces |
| `DEBUG` | boolean | `false` | Must be `false` in production |
| `API_V1_PREFIX` | string | `/api/v1` | Base route prefix |
| `CORS_ORIGINS` | string | `https://safety.yourdomain.com` | Strict production domain(s); never `*` |
| `DATABASE_URL` | string | `postgresql+asyncpg://app_user:PROD_PASS@db-cluster.internal:5432/roadsafety_prod` | TLS-encrypted async PostgreSQL connection |
| `STORAGE_BACKEND` | string | `local` | `local` or cloud object store (S3/GCS) |
| `UPLOAD_DIR` | string | `static/uploads` | Path for validated hazard evidence |
| `MAX_UPLOAD_SIZE_MB` | integer | `10` | Hard ceiling for citizen photo evidence |
| `SECRET_KEY` | string | `GENERATE_LONG_SECURE_RANDOM_KEY_MIN_64_CHARS` | Minimum 64-character random string |
| `ALGORITHM` | string | `HS256` | JWT signing algorithm |
| `ACCESS_TOKEN_EXPIRE_MINUTES`| integer | `1440` | Token expiry duration |
| `ROAD_DAMAGE_MODEL_PATH` | string | `app/ml/artifacts/road_damage_yolo.pt` | Path to genuine trained YOLOv8 checkpoint |
| `ML_DEVICE` | string | `cuda` (or `cpu`) | Acceleration hardware device |
| `DAMAGE_CONFIDENCE_THRESHOLD` | float | `0.25` | Minimum detection confidence |

### Frontend Environment Variables (`frontend/.env`)

| Variable | Example Production Value | Purpose |
| :--- | :--- | :--- |
| `VITE_API_BASE_URL` | `https://api.safety.yourdomain.com` | Backend API URL |
| `VITE_OSM_TILE_SERVER` | `https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png` | Tile server URL |
| `VITE_DEFAULT_MAP_LAT` | `12.9716` | Initial map center latitude (Bengaluru) |
| `VITE_DEFAULT_MAP_LON` | `77.5946` | Initial map center longitude (Bengaluru) |
| `VITE_DEFAULT_MAP_ZOOM` | `12` | Initial zoom level |

---

## 4. Production Database Provisioning (PostgreSQL & PostGIS)

### Step 1: Database Creation & PostGIS Activation
Connect to your PostgreSQL cluster as an administrative user (`postgres`):
```sql
-- Create dedicated production database
CREATE DATABASE roadsafety_prod;

-- Connect to database
\c roadsafety_prod

-- Enable PostGIS spatial extension
CREATE EXTENSION IF NOT EXISTS postgis;

-- Verify extension installation
SELECT PostGIS_Version();

-- Create least-privilege application user
CREATE USER roadsafety_app WITH PASSWORD 'CHANGE_TO_COMPLEX_PASSWORD';
GRANT ALL PRIVILEGES ON DATABASE roadsafety_prod TO roadsafety_app;
GRANT ALL ON SCHEMA public TO roadsafety_app;
```

### Step 2: Safe Migration Backfill
Run the geometry backfill migration script:
```powershell
# Run dry-run first to inspect pending records safely
python backend/scripts/migrate_hazard_geom.py --dry-run

# Execute migration in a single atomic transaction
python backend/scripts/migrate_hazard_geom.py --execute
```

### Step 3: Seed Verified Emergency Facilities
Populate verified public health reference facilities:
```powershell
# Safe dry-run inspection
python backend/scripts/seed_verified_hospitals.py --dry-run

# Idempotent execution
python backend/scripts/seed_verified_hospitals.py --execute
```

---

## 5. Machine Learning Checkpoint Deployment

Model artifacts are excluded from Git to prevent repository bloat and ensure model provenance:

1. **Road Distress Detection Model (`YOLOv8`)**:
   - Required Path: `backend/app/ml/artifacts/road_damage_yolo.pt`
   - Verification: Confirm genuine checkpoint exists and passes SHA-256 integrity validation.
   - Fallback State: When weights are omitted, the API responds with `503 Service Unavailable (MODEL_UNAVAILABLE)` with clear status details.
2. **Accident Risk Model (`XGBoost`)**:
   - Required Path: `backend/app/ml/artifacts/accident_risk_xgb.json`
   - Auxiliary Artifact: `backend/app/ml/artifacts/preprocessor.joblib`
   - Fallback State: When uncalibrated or unweighted, responds with `503 Service Unavailable (MODEL_UNAVAILABLE)` while continuing to provide real-time spatial hazard density.

---

## 6. Web Server & Reverse Proxy Configuration

### System Architecture
```text
[ Client Browser ]
        │
   HTTPS (Port 443)
        ▼
[ Nginx / Caddy Reverse Proxy ]
   ├── /               ──> [ Frontend SPA: /var/www/roadsafety/frontend/dist ]
   ├── /api/           ──> [ Gunicorn/Uvicorn Workers: 127.0.0.1:8000 ]
   ├── /health         ──> [ Backend Health Probe: 127.0.0.1:8000/health ]
   └── /static/uploads ──> [ Uploads Directory: /var/www/roadsafety/static/uploads ]
```

### Production ASGI Execution
Run FastAPI using Gunicorn with Uvicorn worker processes:
```bash
gunicorn app.main:app \
  --workers 4 \
  --worker-class uvicorn.workers.UvicornWorker \
  --bind 127.0.0.1:8000 \
  --access-logfile /var/log/roadsafety/access.log \
  --error-logfile /var/log/roadsafety/error.log \
  --timeout 60
```

---

## 7. Health Checks and Production Smoke Tests

Automated health checks can be integrated into Kubernetes readiness/liveness probes or load balancer health monitors:

### Automated Endpoint Probes

1. **Root Health Check**:
   ```bash
   curl -s -f https://api.safety.yourdomain.com/health | jq .
   ```
   **Expected Response (200 OK):**
   ```json
   {
     "status": "healthy",
     "project_name": "AI-Powered Road and Vehicle Safety System",
     "version": "0.1.0",
     "environment": "production",
     "database": {
       "connected": true,
       "database_url_configured": true,
       "postgis_enabled": true,
       "postgis_version": "3.4 USE_GEOS=1 USE_PROJ=1 USE_STATS=1",
       "server_version": "PostgreSQL 16.3 on x86_64-pc-linux-gnu",
       "error": null,
       "setup_guidance": null
     }
   }
   ```

2. **Hospital Proximity Smoke Test**:
   ```bash
   curl -s "https://api.safety.yourdomain.com/api/v1/hospitals/nearby?latitude=12.9716&longitude=77.5946&radius_meters=10000" | jq .
   ```
   **Assertions:**
   - HTTP status `200`
   - `total_found` $\ge 1$
   - Results sorted strictly ascending by `straight_line_distance_meters`
   - `disclaimer` and emergency helplines (`112`, `108`) present

3. **Vehicle Statutory Standards Smoke Test**:
   ```bash
   curl -s https://api.safety.yourdomain.com/api/v1/vehicles/standards | jq .
   ```
   **Assertions:**
   - HTTP status `200`
   - Citations present for CMVR 1989 Rules 95, 96, 115, 52/62, and MVA 1988
   - Disclaimer version present

4. **Model Unavailability Honesty Check**:
   ```bash
   curl -s -X POST https://api.safety.yourdomain.com/api/v1/risk/predict \
     -H "Content-Type: application/json" \
     -d '{"latitude": 12.9716, "longitude": 77.5946, "road_classification": "urban_arterial", "speed_limit_kmh": 50, "surface_condition": "dry", "lighting_condition": "daylight", "weather_condition": "clear", "search_radius_meters": 1000}' | jq .
   ```
   **Assertions:**
   - If weights not present, returns HTTP `503` with `"error": "MODEL_UNAVAILABLE"`
   - Confirms no mock/random probabilities are returned

---

## 8. Incident Response & Rollback Runbook

1. **Database Degradation:**
   - If PostgreSQL or PostGIS becomes unreachable, the backend automatically switches to exact Haversine mathematical calculation on standard coordinates.
   - The UI displays an amber notification: `Degraded (Spatial Fallback Engine Active)`.
2. **Model Failure:**
   - If inference fails, the API returns a structured HTTP `503` error without crashing the server.
   - The UI offers the option to prefill a standard citizen report rather than halting user workflow.
3. **Emergency Helplines:**
   - National helplines (112, 108, 100, 103) are rendered via static HTML and client-side links, ensuring continuous availability even if the backend API is temporarily offline.
