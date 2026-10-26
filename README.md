# AI-Powered Road and Vehicle Safety System (`AI-Road-Vehicle-Safety-System`)

An end-to-end intelligent safety platform combining road hazard detection, preliminary vehicle condition assessment under Indian technical standards (CMVR Rule 95 / AIS-044), corridor accident-risk prediction with Explainable AI (TreeSHAP), and emergency trauma advisory navigation.

---

## Architecture Overview

- **Backend**: FastAPI (Python 3.11+ / 3.13+) with async SQLAlchemy 2.0, Pydantic v2 Settings, and PostGIS spatial indexing.
- **Frontend**: React 18, Vite, TypeScript, Tailwind CSS, Leaflet, and OpenStreetMap (EPSG:4326).
- **Database**: PostgreSQL 16/17 + PostGIS 3.4 spatial extension.
- **AI Modules (Phases 3 & 5)**:
  - Road Hazard Detection: YOLOv8 fine-tuned on RDD2020 road distress dataset (potholes, cracks).
  - Vehicle Safety Assessment: Transparent, rule-based CMVR Rule 95 / AIS wear evaluation.
  - Accident Risk Model: XGBoost classifier with TreeSHAP feature attributions.

---

## Project Structure

```text
AI-Road-Vehicle-Safety-System/
├── backend/
│   ├── app/
│   │   ├── api/v1/
│   │   │   ├── endpoints/
│   │   │   │   └── health.py          # GET /health & /api/v1/health
│   │   │   └── router.py
│   │   ├── core/
│   │   │   ├── config.py              # Pydantic BaseSettings
│   │   │   └── database.py            # Async engine, session & PostGIS probe
│   │   ├── models/                    # ORM tables: Hazard, VehicleAssessment, Hospital
│   │   ├── schemas/                   # Pydantic v2 request/response schemas
│   │   └── main.py                    # FastAPI application entrypoint & CORS
│   ├── static/uploads/                # Local hazard image storage (dev)
│   ├── tests/                         # Pytest test suite (health & model tests)
│   ├── requirements.txt
│   ├── pytest.ini
│   └── .env.example
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   │   ├── common/                # StatusBadge, DisclaimerBanner
│   │   │   ├── layout/                # Navbar, Footer
│   │   │   └── map/                   # Leaflet MapContainer with OSM tiles
│   │   ├── services/api.ts            # Backend health & data client
│   │   ├── types/index.ts             # TypeScript interfaces
│   │   ├── App.tsx                    # Main responsive dashboard shell
│   │   └── main.tsx
│   ├── package.json
│   ├── vite.config.ts
│   ├── tsconfig.json
│   └── .env.example
├── .gitignore
└── README.md
```

---

## Windows Local Setup Instructions (PowerShell)

### 1. Prerequisites
- **Python**: 3.11+ (installed and added to PATH)
- **Node.js**: v18+ or v20+ LTS
- **PostgreSQL**: Version 16 or 17 with PostGIS extension

---

### 2. Database & PostGIS Setup

#### Option A: Native Windows PostgreSQL
1. Open PowerShell and verify PostgreSQL connectivity:
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
   *(Note: If PostGIS is not yet installed in your local PostgreSQL, run Stack Builder from the Windows Start Menu, expand "Spatial Extensions", and select PostGIS).*

#### Option B: PostGIS via Docker (Alternative)
```powershell
docker run --name postgis-roadsafety -e POSTGRES_PASSWORD=postgres -e POSTGRES_DB=roadsafety_db -p 5432:5432 -d postgis/postgis:16-3.4
```

---

### 3. Backend Setup & Run

1. Navigate to `backend` and create a virtual environment:
   ```powershell
   cd backend
   python -m venv venv
   .\venv\Scripts\Activate.ps1
   ```
2. Install Python dependencies:
   ```powershell
   pip install -r requirements.txt
   ```
3. Configure environment variables:
   ```powershell
   Copy-Item .env.example .env
   # Update DATABASE_URL in .env with your local PostgreSQL password:
   # DATABASE_URL="postgresql+asyncpg://postgres:YOUR_PASSWORD@localhost:5432/roadsafety_db"
   ```
4. Run the test suite:
   ```powershell
   pytest -v
   ```
5. Start the FastAPI development server:
   ```powershell
   uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
   ```
6. Open your browser:
   - Interactive Swagger API Docs: [http://127.0.0.1:8000/api/v1/docs](http://127.0.0.1:8000/api/v1/docs)
   - Health Probe: [http://127.0.0.1:8000/health](http://127.0.0.1:8000/health)

---

### 4. Frontend Setup & Run

1. Open a new PowerShell terminal and navigate to `frontend`:
   ```powershell
   cd frontend
   npm install
   ```
2. Configure frontend environment variables:
   ```powershell
   Copy-Item .env.example .env
   ```
3. Build for production verification:
   ```powershell
   npm run build
   ```
4. Start the Vite development server:
   ```powershell
   npm run dev
   ```
5. Open your browser at [http://localhost:5173](http://localhost:5173).

---

## Phase 1 Status & Safeguards

- **Zero Fake Predictions**: No mock scores or AI results are presented in Phase 1.
- **Accurate Health Probe**: `GET /health` reports the real connection status of PostgreSQL and PostGIS without falsification.
- **Statutory Alignment**: Vehicle metrics comply with CMVR Rule 95 ($1.6\text{ mm}$ minimum tread limit). All assessments carry preliminary disclaimers.
