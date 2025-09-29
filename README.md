# Location Distance App (FastAPI + Supabase + Plain JS frontend)

This project is a starter web app that lets users pick a source and destination using hierarchical dropdowns (state → district → taluka → village) and shows:
- The distance stored in your `distances` table (Supabase)
- The real-time Google Maps distance (Distance Matrix API) computed using latitude/longitude stored in the `locations` table

## What is included
- `backend/app/main.py` - FastAPI backend with API endpoints to populate dropdowns and fetch distances
- `frontend/` - Simple HTML + JS frontend that calls the backend
- `data/locations_sample.csv` and `data/distances_sample.csv` - sample CSVs you can import into Supabase
- `.env.example` - environment variables needed
- `requirements.txt` - Python dependencies

## Quick setup (local)

1. Extract ZIP and open terminal inside the project folder.

### Linux / macOS
```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# edit .env to add your SUPABASE_URL, SUPABASE_KEY and GOOGLE_MAPS_API_KEY
uvicorn backend.app.main:app --reload --host 0.0.0.0 --port 8000
```
### Windows (PowerShell)
```powershell
python -m venv venv
.env\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.example .env
# edit .env to add keys
uvicorn backend.app.main:app --reload --host 0.0.0.0 --port 8000
```

Open http://localhost:8000/ in your browser — the frontend is served by FastAPI static mount.

## Deploying to Render
1. Push repository to GitHub.
2. Create a new Web Service on Render with Python environment.
3. Build command: `pip install -r requirements.txt`
4. Start command: `gunicorn -k uvicorn.workers.UvicornWorker backend.app.main:app`
5. Add environment variables on Render: `SUPABASE_URL`, `SUPABASE_KEY`, `GOOGLE_MAPS_API_KEY`.

## Database (Supabase) schema notes
Create two tables in Supabase (or import the CSVs in `/data`):

1. `locations` (stores each location and coordinates)
- state_code (text)
- state_name (text)
- district_code (text)
- district_name (text)
- taluka_code (text)     -- optional
- taluka_name (text)     -- optional
- village_code (text)    -- optional
- village_name (text)    -- optional
- full_code (text)       -- **unique code constructed as** state(2) + district(2) + taluka(2) + village(3), e.g. `010101001`
- latitude (float)
- longitude (float)

2. `distances`
- source_code (text)  -- matches locations.full_code
- source_name (text)
- dest_code (text)    -- matches locations.full_code
- dest_name (text)
- distance_km (float)

**Latitude/Longitude** belongs in the `locations` table (one lat/lng per `full_code`).

## How codes are constructed in the frontend
The frontend will construct a 9-digit `full_code` with this pattern:
- state = 2 digits
- district = 2 digits
- taluka = 2 digits (or '00' if missing)
- village = 3 digits (or '000' if missing)

E.g. `01` (state) + `01` (district) + `01` (taluka) + `001` (village) = `010101001`

If your distance records are at village-level, the user must select the village for accurate lookup. If you store distances at higher levels, ensure the codes in `distances` are consistent with the concatenation rules above.

---
If you want, I can now:
- Help you import the sample CSVs into Supabase (I can give step-by-step instructions)
- Convert the frontend to React later
- Add authentication if you want user-specific history