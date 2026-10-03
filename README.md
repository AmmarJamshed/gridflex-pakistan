# GRIDFLEX Pakistan

**Turn unused electricity flexibility into value.**

A research/prototype platform for a Pakistan-focused **electricity flexibility marketplace**. It coordinates demand response, distributed energy resources, aggregators, and financial settlement — while keeping physical power flow governed by the grid.

> **Prototype notice:** Simulated prices, illustrative grid zones, and demo data. Not an operational market and not a legally authorized electricity trading system.

## What it does

1. Monitors simulated smart-meter / DER telemetry  
2. Classifies loads (base / shiftable / curtailable / storage / generation)  
3. Matches flexibility offers and bids within **grid zones / feeders**  
4. Clears markets, settles wallets, and forecasts demand / solar / flexibility  
5. Detects anomalous flexibility claims  
6. Runs a one-click Pakistan GridFlex simulation (before vs after)

## Architecture (conceptual)

| Layer | Role |
|-------|------|
| Physical grid | Power flows per network physics (DISCOs / NTDC) |
| Flexibility accounting | Verified kW/kWh changes → digital credits |
| Marketplace | Zone-constrained offers, bids, clearing |
| Settlement | PKR wallets, platform & grid fees |
| AI / fraud | Forecasts + anomaly flags |

Electricity does **not** travel peer-to-peer from User A to User B. See in-app **Flexibility Accounting Layer**.

## Stack

- **Frontend:** React, TypeScript, Tailwind CSS, Recharts  
- **Backend:** Python, FastAPI, WebSockets, JWT  
- **Database:** Supabase-compatible SQL (SQLite locally by default)  
- **Analytics / ML:** Pandas, NumPy, Scikit-learn  
- **Simulation:** Python engine for 10k+ participants  

## Quick start

### Prerequisites

- Python 3.11+  
- Node.js 20+  
- Docker (optional)

### Backend

```bash
cd backend
python -m venv .venv
# Windows:
.venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

API docs: http://localhost:8000/docs

### Frontend

```bash
cd frontend
npm install
npm run dev
```

App: http://localhost:5173

### Docker (full stack)

```bash
docker compose up --build
```

- Frontend: http://localhost:5173  
- API: http://localhost:8000  
- Postgres: localhost:5432  

### Public deploy

| Piece | Host | URL |
|-------|------|-----|
| Frontend | Netlify | https://gridflex-pakistan.netlify.app |
| Repo | GitHub | https://github.com/AmmarJamshed/gridflex-pakistan |
| API (always-on) | Render (one-click) | [Deploy API](https://render.com/deploy?repo=https://github.com/AmmarJamshed/gridflex-pakistan) |
| Frontend (alt) | Vercel | [Import to Vercel](https://vercel.com/new/clone?repository-url=https://github.com/AmmarJamshed/gridflex-pakistan&root-directory=frontend) |

After the Render API is live, set Netlify env `VITE_API_URL` to that HTTPS URL and trigger a rebuild.  
Vercel CLI login was not available in this environment; use the Import link above or `vercel login` locally.

### Demo credentials

| Role | Email | Password |
|------|-------|----------|
| Consumer | consumer@gridflex.pk | demo1234 |
| Aggregator | aggregator@gridflex.pk | demo1234 |
| Utility | utility@gridflex.pk | demo1234 |
| Admin | admin@gridflex.pk | demo1234 |

### One-click demo

Open **Simulation** → **RUN PAKISTAN GRIDFLEX SIMULATION**

## Project structure

```
gridflex-pakistan/
├── frontend/          # React dashboards
├── backend/           # FastAPI API + engines
├── simulation/        # Standalone simulation helpers
├── ml/                # Forecasting & anomaly models
├── database/          # Supabase SQL schema
├── docs/              # Architecture & API notes
├── data/              # Sample datasets
├── tests/             # Automated tests
└── docker-compose.yml
```

## Dashboards

| Route | Audience |
|-------|----------|
| `/` | Landing + concept |
| `/consumer` | Residential / commercial / prosumer |
| `/aggregator` | Virtual power resource view |
| `/market` | Offers, bids, clearing |
| `/grid` | Utility / operator |
| `/admin` | Config, fraud, demo controls |
| `/regulatory` | Pakistan regulatory compatibility |
| `/simulation` | Before/after GridFlex demo |

## Economic model (configurable)

Prototype defaults (not real tariffs):

- Platform fee: 5%  
- Grid/utility fee: 2%  
- Normal flex price ~ PKR 8/kWh  
- Peak ~ PKR 15/kWh  
- Critical ~ PKR 25/kWh  

## License

Research / educational prototype. Not for operational market use.