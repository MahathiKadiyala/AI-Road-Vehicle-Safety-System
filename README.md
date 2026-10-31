# AI-Powered Road and Vehicle Safety System (`AI-Road-Vehicle-Safety-System`)

An end-to-end intelligent road and vehicle safety platform designed around the complete safety lifecycle:

$$\textbf{Prevent} \longrightarrow \textbf{Detect} \longrightarrow \textbf{Predict} \longrightarrow \textbf{Explain} \longrightarrow \textbf{Respond}$$

Combining citizen road hazard reporting, high-performance spatial GIS density, road surface distress computer vision, transparent rule-based vehicle safety evaluations under Indian statutory standards (CMVR 1989 Rule 95 / AIS-044), explainable corridor accident-risk modeling (TreeSHAP), and emergency trauma advisory navigation.

---

## 1. Safety Lifecycle Architecture

```text
┌────────────────────────────────────────────────────────────────────────────────┐
│                           ROAD & VEHICLE SAFETY PLATFORM                       │
└──────────────────────────────────────┬─────────────────────────────────────────┘
                                       │
     ┌─────────────────────────────────┼─────────────────────────────────┐
     ▼                                 ▼                                 ▼
┌──────────────┐              ┌────────────────┐              ┌────────────────┐
│   PREVENT    │              │     DETECT     │              │    PREDICT     │
│ CMVR 1989    │              │ YOLOv8 Road    │              │ XGBoost Risk   │
│ Vehicle Wear │              │ Distress &     │              │ Pipeline &     │
│ Assessments  │              │ Citizen Hazard │              │ PostGIS Hazard │
│ (Rule 95/AIS)│              │ Reporting      │              │ Density Engine │
└──────────────┘              └────────────────┘              └────────────────┘
                                       │
                                       ├─────────────────────────────────┐
                                       ▼                                 ▼
                              ┌────────────────┐              ┌────────────────┐
                              │    EXPLAIN     │              │    RESPOND     │
                              │ TreeSHAP       │              │ PostGIS Trauma │
                              │ Attributions & │              │ Center Locator │
                              │ Deterministic  │              │ & Emergency    │
                              │ Audit Reports  │              │ 112/108 Matrix │
                              └────────────────┘              └────────────────┘
```

1. **Prevent (Vehicle Condition & Statutory Compliance — Phase 4):** Deterministic, rule-based vehicle evaluations distinguishing statutory safety floors (CMVR Rule 95 $1.6\text{ mm}$ tyre wear floor for cars, $0.8\text{ mm}$ for 2/3-wheelers) from manufacturer maintenance thresholds (brake lining discard at $<2.0\text{ mm}$).
2. **Detect (Hazard Reporting & Road Distress AI — Phases 2 & 3):** Citizen road hazard logging with content-inspected image uploads, paired with YOLOv8 inference for detecting cracks (longitudinal D00, transverse D10, alligator D20) and potholes (D40).
3. **Predict (PostGIS Density & Accident Risk — Phases 5.1 & 5.2):** Meter-accurate spatial hazard density queries using PostGIS geography casting (`ST_DWithin` on SRID 4326), integrated into an XGBoost accident-risk prediction pipeline.
4. **Explain (Transparency & Interpretability — Phases 4 & 5.2):** Parameter-by-parameter statutory citations for vehicle ratings, and calibrated feature importance attributions for corridor risk factors. Zero black-box opacity.
5. **Respond (Emergency Trauma Proximity — Phase 5.3):** Proximity discovery of verified trauma centers and casualty wards using PostGIS meter distance and Haversine fallback, with one-click direct dialing for national emergency helplines (`112`, `108`, `100`, `103`).

---

## 2. System Architecture & Tech Stack

```text
[ Browser / Mobile Client ]
         │
         ▼ HTTP / REST
┌────────────────────────────────────────────────────────────────────────┐
│                        FastAPI Application (v0.1.0)                    │
│                                                                        │
│  [ Security & Headers ]  OWASP (nosniff, DENY, Referrer-Policy, CORS)   │
│  [ Global Handlers ]     Masked stack traces; sanitized JSON 500s      │
│  [ Content Inspection ]  Magic-byte headers, UUID4 files, max 10 MB    │
│  [ Storage Handler ]     Path traversal containment within uploads/    │
│                                                                        │
│  [ Routers & Modules ]                                                 │
│    ├── /health           System connectivity & PostGIS diagnostic      │
│    ├── /api/v1/hazards   Citizen reports & PostGIS spatial density     │
│    ├── /api/v1/damage    YOLOv8 distress inference & status checks     │
│    ├── /api/v1/vehicles  CMVR 1989 / AIS rule engine & standards      │
│    ├── /api/v1/risk      Accident-risk pipeline & TreeSHAP             │
│    └── /api/v1/hospitals PostGIS proximity & emergency advisories      │
└──────────────────┬─────────────────────────────┬───────────────────────┘
                   │                             │
                   ▼                             ▼
┌──────────────────────────────────┐ ┌───────────────────────────────────┐
│     Spatial Database Engine      │ │       Machine Learning Engine     │
│  PostgreSQL 16/17 + PostGIS 3.4  │ │                                   │
│  - Geography Casting (meters)    │ │  - Ultralytics YOLOv8 (Distress)  │
│  - POINT(lon lat) SRID 4326      │ │  - XGBoost Classifier (Risk)      │
│  - GIST Spatial Indices          │ │  - TreeSHAP & Brier Calibration   │
│  - Safe Haversine Math Fallback  │ │  - Honest 503 if weights omitted  │
└──────────────────────────────────┘ └───────────────────────────────────┘
```

- **Backend**: FastAPI (Python 3.11 / 3.13), async SQLAlchemy 2.0 with asyncpg, GeoAlchemy2, Pydantic v2 Settings.
- **Frontend**: React 18, Vite 5, TypeScript, Tailwind CSS, Lucide icons, Leaflet with OpenStreetMap tiles (WGS84 EPSG:4326).
- **Spatial Engine**: PostgreSQL 16/17 + PostGIS 3.4 with Geography distance calculations and automatic Haversine fallback.
- **Reliability & Security**: Resilient frontend fetch with request timeouts and bounded retries; credential-scrubbed logging; OWASP response headers.

---

## 3. Project Directory Structure

```text
AI-Road-Vehicle-Safety-System/
├── backend/
│   ├── app/
│   │   ├── api/v1/
│   │   │   ├── endpoints/
│   │   │   │   ├── damage.py              # Road distress AI inference (POST /detect, GET /status)
│   │   │   │   ├── hazards.py             # Citizen hazard reporting & spatial density
│   │   │   │   ├── health.py              # System diagnostics & PostGIS probe (GET /health)
│   │   │   │   ├── hospitals.py           # Verified trauma facility proximity lookup
│   │   │   │   ├── risk.py                # Corridor accident-risk prediction & status
│   │   │   │   └── vehicles.py            # CMVR 1989 vehicle compliance engine & standards
│   │   │   └── router.py                  # Consolidated v1 API router
│   │   ├── core/
│   │   │   ├── config.py                  # Pydantic BaseSettings & CORS origins
│   │   │   ├── database.py                # Async SQLAlchemy engine, session & error sanitizer
│   │   │   ├── spatial.py                 # PostGIS ST_DWithin queries & Haversine fallback
│   │   │   ├── storage.py                 # Magic-byte validation, UUID filenames & path defense
│   │   │   └── vehicle_rules.py           # CMVR Rule 95 / AIS statutory rule evaluation logic
│   │   ├── ml/
│   │   │   ├── artifacts/                 # Checkpoints directory (gitignored: .pt, .json)
│   │   │   ├── dataset/
│   │   │   │   ├── convert_rdd.py         # RDD2020 XML to YOLO dataset converter
│   │   │   │   └── validate_yolo.py       # Dataset structure, label bounds & pair validator
│   │   │   ├── risk/
│   │   │   │   ├── metrics.py             # ROC-AUC, PR-AUC, Brier score calibration metrics
│   │   │   │   ├── predictor.py           # RiskPredictor with honest unavailable status
│   │   │   │   └── train.py               # Leakage-free baseline risk trainer & CV splits
│   │   │   └── detector.py                # RoadDamageDetector YOLO worker with thread offload
│   │   ├── models/                        # ORM models: Hazard, Hospital, VehicleAssessment
│   │   ├── schemas/                       # Pydantic v2 schemas: hazard, damage, vehicle, risk, hospital
│   │   └── main.py                        # FastAPI entrypoint, security headers & error handlers
│   ├── scripts/
│   │   ├── migrate_hazard_geom.py         # Idempotent PostGIS geometry backfill migration
│   │   └── seed_verified_hospitals.py     # Idempotent verified emergency hospital seeder
│   ├── tests/                             # Pytest suite: 167 tests (unit, integration, security)
│   ├── requirements.txt                   # Production and ML dependencies
│   ├── pytest.ini                         # Pytest configuration
│   └── .env.example                       # Documented environment template (no real secrets)
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   │   ├── common/                    # StatusBadge, DisclaimerBanner
│   │   │   ├── damage/                    # DamageDetectionView (visualizer & inspector)
│   │   │   ├── emergency/                 # EmergencySupportView (locator & 112/108 helplines)
│   │   │   ├── hazards/                   # HazardReportForm & HazardReportCard
│   │   │   ├── layout/                    # Navbar, Footer
│   │   │   ├── map/                       # Leaflet MapContainer (WGS84 markers & density)
│   │   │   ├── risk/                      # AccidentRiskView (pipeline status & metrics)
│   │   │   └── vehicle/                   # VehicleAssessmentView (CMVR audit & standards)
│   │   ├── services/
│   │   │   └── api.ts                     # Resilient API client (timeouts, safe bounded retries)
│   │   ├── types/                         # TypeScript interfaces and domain schemas
│   │   ├── App.tsx                        # Master multi-tab responsive safety dashboard
│   │   └── main.tsx
│   ├── package.json
│   ├── vite.config.ts
│   ├── tsconfig.json
│   └── .env.example
├── docs/
│   └── DEPLOYMENT.md                      # Production deployment & operations checklist
├── .gitignore                             # Comprehensive secret, build & artifact exclusions
└── README.md
```

---

## 4. API Reference Table

All API endpoints are prefixed with `/api/v1` (with the exception of root `/health`).

| Method | Endpoint | Description | Request Body / Query Params | Response Schema |
| :--- | :--- | :--- | :--- | :--- |
| `GET` | `/health` | Diagnostic health probe & PostGIS status | None | `HealthResponse` |
| `GET` | `/api/v1/health` | API v1 health status & version metadata | None | `HealthResponse` |
| `POST` | `/api/v1/hazards` | Submit citizen road hazard observation | Multipart: `title`, `latitude`, `longitude`, `hazard_type`, `severity`, `image` | `HazardRead` |
| `GET` | `/api/v1/hazards` | List hazard reports with filtering | Query: `hazard_type`, `severity`, `status`, `skip`, `limit` | `List[HazardRead]` |
| `GET` | `/api/v1/hazards/density` | Compute spatial density within radius | Query: `latitude`, `longitude`, `radius_meters` | `HazardDensityResponse` |
| `GET` | `/api/v1/hazards/{id}` | Retrieve specific hazard report by UUID | Path: `id` | `HazardRead` |
| `GET` | `/api/v1/damage/status` | YOLOv8 model operational status & classes | None | `DamageModelStatusResponse` |
| `POST` | `/api/v1/damage/detect` | Run distress inference on road photo | Multipart: `image`, `confidence_threshold` | `DamageDetectionResponse` |
| `GET` | `/api/v1/vehicles/standards` | Authoritative Indian standards registry | None | `VehicleStandardsResponse` |
| `POST` | `/api/v1/vehicles/assess` | Rule-based CMVR 95 compliance evaluation | JSON: `make`, `model`, `year`, `odometer_km`, `vehicle_category`, `tyre_tread_depth_mm`, `brake_pad_thickness_mm`, `disclaimer_acknowledged` | `VehicleAssessmentRead` |
| `GET` | `/api/v1/vehicles/{id}` | Retrieve persisted vehicle evaluation | Path: `id` | `VehicleAssessmentRead` |
| `GET` | `/api/v1/risk/status` | Accident-risk model provenance & state | None | `RiskModelStatusResponse` |
| `POST` | `/api/v1/risk/predict` | Predict road-segment accident risk index | JSON: `latitude`, `longitude`, `road_classification`, `speed_limit_kmh`, `surface_condition`, `weather_condition`, `lighting_condition`, `search_radius_meters` | `RiskPredictionResponse` |
| `GET` | `/api/v1/hospitals/nearby` | Proximity search for emergency facilities | Query: `latitude`, `longitude`, `radius_meters`, `emergency_only`, `limit` | `NearbyHospitalsResponse` |
| `GET` | `/api/v1/hospitals/{id}` | Retrieve hospital details by UUID | Path: `id` | `HospitalRead` |

Interactive OpenAPI documentation is served at [http://127.0.0.1:8000/api/v1/docs](http://127.0.0.1:8000/api/v1/docs).

---

## 5. Machine Learning Models, Training & Honest Status

### A. Road Damage Detection (YOLOv8)

- **Target Classes**:
  - `0: D00` — Linear Longitudinal Crack
  - `1: D10` — Linear Transverse Crack
  - `2: D20` — Alligator / Map Crack
  - `3: D40` — Pothole
- **Dataset Specification**: Formatted in YOLO coordinate bounding boxes ($[0, 1]$ normalized `class_id x_center y_center width height`). Converted from RDD2020 Pascal VOC XML annotations via:
  ```powershell
  python backend/app/ml/dataset/convert_rdd.py --rdd-dir ./datasets/rdd2020 --output-dir ./datasets/yolo_rdd
  ```
- **Validation**: Verify image/label pairing, coordinate bounds, and split separation:
  ```powershell
  python backend/app/ml/dataset/validate_yolo.py --dataset-dir ./datasets/yolo_rdd
  ```
- **Reproducible Training Command**:
  ```powershell
  yolo detect train data=datasets/yolo_rdd/data.yaml model=yolov8n.pt epochs=50 imgsz=640 seed=42
  ```
- **Checkpoint Location**: `backend/app/ml/artifacts/road_damage_yolo.pt`
- **Current Operational Status**:
  - Model converter, dataset validator, inference service, and visualizer are **100% complete and tested**.
  - Trained neural network weights are excluded from Git to prevent repository bloat. When the weights file is absent, the backend reports honest `503 SERVICE_UNAVAILABLE (MODEL_UNAVAILABLE)` status and never outputs fake or random detections.

### B. Corridor Accident-Risk Prediction (XGBoost + TreeSHAP)

- **Target Definition**: Segment accident frequency / severity index classification.
- **Dataset Schema**: Standardized tabular schema (`segment_id`, `latitude`, `longitude`, `speed_limit_kmh`, `surface_condition`, `lighting_condition`, `weather_condition`, `spatial_hazard_density`, `target_accident`).
- **Target Leakage Prevention**: Enforces temporal cross-validation splitting (training on historical timeframes, testing on strictly subsequent periods) to avoid lookahead leakage.
- **Reproducible Baseline Training**:
  ```powershell
  python backend/app/ml/risk/train.py --data-path ./datasets/accidents/processed_accidents.csv --output-dir ./backend/app/ml/artifacts/ --seed 42
  ```
- **Probabilistic Calibration & Evaluation**:
  - Validates probabilistic calibration using **Brier Score**, **ROC-AUC**, and **PR-AUC** via `backend/app/ml/risk/metrics.py`.
- **Checkpoint Location**:
  - Model: `backend/app/ml/artifacts/accident_risk_xgb.json`
  - Preprocessor: `backend/app/ml/artifacts/preprocessor.joblib`
- **Current Operational Status**:
  - Feature processing pipeline, spatial hazard integration, validation metrics, and API endpoints are **100% complete and tested**.
  - Returns honest `503 SERVICE_UNAVAILABLE (MODEL_UNAVAILABLE)` with transparent provenance disclosures until calibrated on verified departmental crash records. The spatial hazard density metrics continue to be computed in real-time.

---

## 6. Windows Local Setup Instructions (PowerShell)

### Step 1: Clone & Verify System Prerequisites
- **Python**: 3.11+ or 3.13 (added to Windows `PATH`)
- **Node.js**: v18+ or v20+ LTS
- **PostgreSQL**: 16 or 17 with PostGIS spatial extension

### Step 2: PostgreSQL & PostGIS Setup

#### Option A: Native Windows PostgreSQL
1. Open PowerShell and verify connectivity:
   ```powershell
   psql -U postgres
   ```
2. Create the project database and activate PostGIS:
   ```sql
   CREATE DATABASE roadsafety_db;
   \c roadsafety_db
   CREATE EXTENSION IF NOT EXISTS postgis;
   SELECT PostGIS_Version();
   \q
   ```
   *(If PostGIS is not installed, open Windows Start Menu, run "Application Stack Builder", expand "Spatial Extensions", and install PostGIS).*

#### Option B: Docker Container Alternative
```powershell
docker run --name postgis-roadsafety -e POSTGRES_PASSWORD=postgres -e POSTGRES_DB=roadsafety_db -p 5432:5432 -d postgis/postgis:16-3.4
```

### Step 3: Backend Setup & Testing

1. Open PowerShell, navigate to `backend`, and create a virtual environment:
   ```powershell
   cd backend
   python -m venv venv
   .\venv\Scripts\Activate.ps1
   ```
2. Install Python dependencies:
   ```powershell
   pip install -r requirements.txt
   ```
3. Initialize the environment configuration:
   ```powershell
   Copy-Item .env.example .env
   # Edit .env to set your PostgreSQL password:
   # DATABASE_URL="postgresql+asyncpg://postgres:YOUR_PASSWORD@localhost:5432/roadsafety_db"
   ```
4. Run migrations and seed verified reference facilities safely:
   ```powershell
   # Backfill PostGIS geometry (dry-run first)
   python scripts/migrate_hazard_geom.py --dry-run
   python scripts/migrate_hazard_geom.py --execute

   # Seed verified emergency facilities (dry-run first)
   python scripts/seed_verified_hospitals.py --dry-run
   python scripts/seed_verified_hospitals.py --execute
   ```
5. Run the comprehensive test suite (166+ passing tests):
   ```powershell
   pytest -v
   ```
6. Start the FastAPI development server:
   ```powershell
   uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
   ```

### Step 4: Frontend Setup & Build

1. Open a second PowerShell terminal and navigate to `frontend`:
   ```powershell
   cd frontend
   npm install
   ```
2. Initialize environment configuration:
   ```powershell
   Copy-Item .env.example .env
   ```
3. Run the production build to verify TypeScript compilation:
   ```powershell
   npm run build
   ```
4. Launch the Vite development server:
   ```powershell
   npm run dev
   ```
5. Open your browser:
   - **Frontend Application**: [http://localhost:5173](http://localhost:5173)
   - **Interactive API Documentation**: [http://127.0.0.1:8000/api/v1/docs](http://127.0.0.1:8000/api/v1/docs)
   - **Backend Health Check**: [http://127.0.0.1:8000/health](http://127.0.0.1:8000/health)

---

## 7. Hospital Data Provenance, Limitations & Emergency Helplines

### Data Provenance & Reference Benchmarks
- Hospital facilities in the seed database represent **registered public health facilities** (e.g., Victoria Hospital, Bowring & Lady Curzon, Manipal Hospital, NIMHANS Trauma Center, St. John's Medical College).
- Facilities are validated for physical latitude/longitude coordinates and listed casualty triage capabilities.
- Bed counts are **static public reference benchmarks** and do **NOT** represent live telemetry or real-time bed availability.

### Geometric Distance Limitations
> [!IMPORTANT]
> **Proximity Approximation Notice:** Distances reported by the API are **straight-line geometric approximations** computed on the WGS84 ellipsoid. They do **NOT** reflect actual road driving distance, traffic congestion, road closures, or emergency vehicle dispatch ETAs.

### Official Emergency Helplines (India)
The platform displays permanent, one-click accessible emergency contacts across all views:
- **`112`** — Unified National Emergency Number (Police, Fire, Ambulance)
- **`108`** — Emergency Medical Ambulance Dispatch (Free 24/7)
- **`100`** — Police Control Room
- **`103`** — Traffic Police Helpline (Accident clearance & lane obstruction)

---

## 8. Security & Release Safeguards

1. **Zero Secret Leaks**: `.env` files and credentials are strictly excluded via `.gitignore`.
2. **Credential Masking**: All database connection URLs are scrubbed via `sanitize_database_error()` to prevent passwords from leaking in health diagnostics or error logs.
3. **OWASP Response Headers**: Enforces `nosniff`, `DENY` frame options, and strict referrer policy.
4. **Safe File Uploads**: Enforces 10 MB maximum size, validates magic bytes (JPEG `FF D8 FF`, PNG `89 50 4E 47`, WEBP `RIFF...WEBP`), rejects control characters and null bytes (`\x00`), and writes files strictly under UUID4 hex filenames to eliminate path traversal vulnerabilities.
5. **Resilient Frontend Communications**: Frontend uses `resilientFetch()` with explicit cancellation timeouts (8s to 30s) and single bounded retries on safe `GET` operations. Non-idempotent `POST` submissions are never auto-retried.
6. **Statutory Integrity**: Vehicle assessments display prominent statutory disclaimers clarifying that evaluations are preliminary estimates under CMVR 1989 Rule 95 and do not certify roadworthiness or substitute for physical technical inspections.
7. **Production Deployment Checklist**: Full production operations, reverse proxy, and monitoring guidelines are maintained in [`docs/DEPLOYMENT.md`](docs/DEPLOYMENT.md).
