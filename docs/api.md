# GRIDFLEX Pakistan API

Base URL: `http://localhost:8000`

Interactive docs: `/docs`

## Auth

- `POST /api/auth/token` JSON `{email,password}` → JWT  
- `POST /api/auth/login` OAuth2 form  
- `GET /api/auth/me`

## Core

| Method | Path | Notes |
|--------|------|-------|
| GET | `/api/grid/status` | National + zone snapshot |
| GET | `/api/grid/zones` | Illustrative zones |
| GET | `/api/market/offers` | Flexibility offers |
| GET | `/api/market/bids` | Flexibility bids |
| POST | `/api/market/clear` | Zone-constrained clearing |
| POST | `/api/simulation/run` | Full Pakistan demo |
| GET | `/api/ai/forecasts` | Demand/flex/solar |
| GET | `/api/fraud/alerts` | Anomaly alerts |
| GET | `/api/concept/flexibility-accounting` | Education layer |
| GET | `/api/concept/regulatory` | NEPRA/NTDC/DISCO notes |
| WS | `/api/ws/live` | Live channel |

All PKR prices are **prototype/simulated**.