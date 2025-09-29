import os
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from supabase import create_client, Client
from dotenv import load_dotenv
import requests

load_dotenv()

SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_KEY = os.getenv('SUPABASE_KEY')
GOOGLE_MAPS_API_KEY = os.getenv('GOOGLE_MAPS_API_KEY')

if not SUPABASE_URL or not SUPABASE_KEY:
    raise RuntimeError('Please set SUPABASE_URL and SUPABASE_KEY in environment variables or .env file')

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

app = FastAPI(title='Location Distance API')

# Allow all origins for development
app.add_middleware(
    CORSMiddleware,
    allow_origins=['*'],
    allow_methods=['*'],
    allow_headers=['*'],
)

# Serve frontend
frontend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'frontend'))
if os.path.isdir(frontend_dir):
    app.mount('/', StaticFiles(directory=frontend_dir, html=True), name='frontend')


def dedupe_and_sort(rows, key_field, name_field):
    seen = {}
    for r in rows:
        k = r.get(key_field)
        n = r.get(name_field)
        if k and n and k not in seen:
            seen[k] = n
    return [{'code': k, 'name': seen[k]} for k in sorted(seen.keys())]


@app.get('/api/states')
def get_states():
    res = supabase.table('locations').select('state_code, state_name').execute()
    rows = res.data or []
    return dedupe_and_sort(rows, 'state_code', 'state_name')


@app.get('/api/districts/{state_code}')
def get_districts(state_code: str):
    res = supabase.table('locations').select('district_code, district_name') \
        .eq('state_code', state_code).execute()
    rows = res.data or []
    return dedupe_and_sort(rows, 'district_code', 'district_name')


@app.get('/api/talukas/{state_code}/{district_code}')
def get_talukas(state_code: str, district_code: str):
    res = supabase.table('locations').select('taluka_code, taluka_name') \
        .eq('state_code', state_code) \
        .eq('district_code', district_code).execute()
    rows = res.data or []
    return dedupe_and_sort(rows, 'taluka_code', 'taluka_name')


@app.get('/api/villages/{state_code}/{district_code}/{taluka_code}')
def get_villages(state_code: str, district_code: str, taluka_code: str):
    res = supabase.table('locations').select('village_code, village_name') \
        .eq('state_code', state_code) \
        .eq('district_code', district_code) \
        .eq('taluka_code', taluka_code).execute()
    rows = res.data or []
    out = [{'code': r['village_code'], 'name': r['village_name']} for r in rows]
    return sorted(out, key=lambda x: x['code'])


@app.get('/api/location/{state_code}/{district_code}/{taluka_code}/{village_code}')
def get_location(state_code: str, district_code: str, taluka_code: str, village_code: str):
    res = supabase.table('locations').select('latitude, longitude, state_name, district_name, taluka_name, village_name') \
        .eq('state_code', state_code) \
        .eq('district_code', district_code) \
        .eq('taluka_code', taluka_code) \
        .eq('village_code', village_code) \
        .limit(1).execute()
    rows = res.data or []
    if not rows:
        raise HTTPException(status_code=404, detail='Location not found')
    return rows[0]


@app.get('/api/distance')
def get_distance(src: str, dest: str):
    # src and dest are full codes: state+district+taluka+village
    src_state, src_dist, src_taluka, src_village = src[:2], src[2:4], src[4:6], src[6:]
    dest_state, dest_dist, dest_taluka, dest_village = dest[:2], dest[2:4], dest[4:6], dest[6:]

    # Database distance
    res = supabase.table('distances').select('distance_km') \
        .eq('source_code', src).eq('dest_code', dest).limit(1).execute()
    rows = res.data or []
    db_distance = rows[0]['distance_km'] if rows else None

    if db_distance is None:
        # try reverse
        res2 = supabase.table('distances').select('distance_km') \
            .eq('source_code', dest).eq('dest_code', src).limit(1).execute()
        rows2 = res2.data or []
        db_distance = rows2[0]['distance_km'] if rows2 else None

    # Google Maps distance
    try:
        src_loc = supabase.table('locations').select('latitude, longitude') \
            .eq('state_code', src_state) \
            .eq('district_code', src_dist) \
            .eq('taluka_code', src_taluka) \
            .eq('village_code', src_village) \
            .limit(1).execute().data

        dest_loc = supabase.table('locations').select('latitude, longitude') \
            .eq('state_code', dest_state) \
            .eq('district_code', dest_dist) \
            .eq('taluka_code', dest_taluka) \
            .eq('village_code', dest_village) \
            .limit(1).execute().data

        if not src_loc or not dest_loc or not GOOGLE_MAPS_API_KEY:
            gmaps_distance = None
        else:
            s = src_loc[0]
            d = dest_loc[0]
            dm_url = f'https://maps.googleapis.com/maps/api/distancematrix/json?origins={s.get("latitude")},{s.get("longitude")}&destinations={d.get("latitude")},{d.get("longitude")}&key={GOOGLE_MAPS_API_KEY}'
            resp = requests.get(dm_url, timeout=10).json()
            gmaps_distance = None
            try:
                elems = resp.get('rows', [])[0].get('elements', [])
                if elems and elems[0].get('status') == 'OK':
                    meters = elems[0].get('distance', {}).get('value')
                    if meters is not None:
                        gmaps_distance = float(meters) / 1000.0
            except Exception:
                gmaps_distance = None
    except Exception:
        gmaps_distance = None

    return {'database_distance_km': db_distance, 'google_maps_distance_km': gmaps_distance}
