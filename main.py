import os
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from supabase import create_client, Client
from dotenv import load_dotenv
from geopy.distance import geodesic
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
    # --- 1. Parsing and Debugging Input ---
    # src and dest are full codes: state(2)+district(2)+taluka(2)+village(3)
    src_state, src_dist, src_taluka, src_village = src[:2], src[2:4], src[4:6], src[6:]
    dest_state, dest_dist, dest_taluka, dest_village = dest[:2], dest[2:4], dest[4:6], dest[6:]

    src_state = int(src_state)      
    src_dist = int(src_dist)     
    src_taluka = int(src_taluka)    
    src_village = int(src_village)
    dest_state = int(dest_state)
    dest_dist = int(dest_dist)
    dest_taluka = int(dest_taluka)
    dest_village = int(dest_village)

    print(f"Source Code: {src} -> S:{src_state}, D:{src_dist}, T:{src_taluka}, V:{src_village}")
    print(f"Dest Code:   {dest} -> S:{dest_state}, D:{dest_dist}, T:{dest_taluka}, V:{dest_village}")
    
    calculated_distance = None # Initialize to None

    try:
        # --- 2. Database Queries ---
        # Note: The Supabase client returns a dictionary with 'data' key for the result.
        src_response = supabase.table('locations').select('latitude, longitude') \
            .eq('state_code', src_state) \
            .eq('district_code', src_dist) \
            .eq('taluka_code', src_taluka) \
            .eq('village_code', src_village) \
            .limit(1).execute()
        src_loc = src_response.data
        
        dest_response = supabase.table('locations').select('latitude, longitude') \
            .eq('state_code', dest_state) \
            .eq('district_code', dest_dist) \
            .eq('taluka_code', dest_taluka) \
            .eq('village_code', dest_village) \
            .limit(1).execute()
        dest_loc = dest_response.data
        
        # --- 3. Debugging Query Results ---
        print(f"Source Location Data: {src_loc}")
        print(f"Dest Location Data:   {dest_loc}")

        # --- 4. Logic for Distance Calculation ---
        if not src_loc or not dest_loc:
            # This is the point where it returns null if data is missing.
            print("Location data missing for one or both points. Returning null.")
        else:
            # src_loc and dest_loc are lists, so access the first element (dictionary)
            s = src_loc[0]
            d = dest_loc[0]
            
            # The .get() method is safer for dictionary access
            src_lat, src_lon = s.get("latitude"), s.get("longitude")
            dest_lat, dest_lon = d.get("latitude"), d.get("longitude")
            
            # Check for valid coordinates
            if src_lat is None or src_lon is None or dest_lat is None or dest_lon is None:
                 print("Latitude or Longitude is NULL in the database. Returning null.")
            else:
                # Calculate straight-line distance 
                src_coords = (src_lat, src_lon)
                dest_coords = (dest_lat, dest_lon)
                
                calculated_distance = geodesic(src_coords, dest_coords).kilometers
                
                # --- 5. Console Output (What you asked for) ---
                print(f"Calculated Distance (km): {calculated_distance}")

    except Exception as e:
        # --- 6. Debugging Exceptions ---
        print(f"An unexpected error occurred: {e}")
        calculated_distance = None
    
    # --- 7. Final Response ---
    return {'database_distance_km': calculated_distance}




    

    # # Database distance
    # res = supabase.table('distances').select('distance_km') \
    #     .eq('source_code', src).eq('dest_code', dest).limit(1).execute()
    # rows = res.data or []
    # db_distance = rows[0]['distance_km'] if rows else None

    # if db_distance is None:
    #     # try reverse
    #     res2 = supabase.table('distances').select('distance_km') \
    #         .eq('source_code', dest).eq('dest_code', src).limit(1).execute()
    #     rows2 = res2.data or []
    #     db_distance = rows2[0]['distance_km'] if rows2 else None

    # # Google Maps distance
    # try:
    #     src_loc = supabase.table('locations').select('latitude, longitude') \
    #         .eq('state_code', src_state) \
    #         .eq('district_code', src_dist) \
    #         .eq('taluka_code', src_taluka) \
    #         .eq('village_code', src_village) \
    #         .limit(1).execute().data

    #     dest_loc = supabase.table('locations').select('latitude, longitude') \
    #         .eq('state_code', dest_state) \
    #         .eq('district_code', dest_dist) \
    #         .eq('taluka_code', dest_taluka) \
    #         .eq('village_code', dest_village) \
    #         .limit(1).execute().data

    #     if not src_loc or not dest_loc or not GOOGLE_MAPS_API_KEY:
    #         gmaps_distance = None
    #     else:
    #         s = src_loc[0]
    #         d = dest_loc[0]
    #         dm_url = f'https://maps.googleapis.com/maps/api/distancematrix/json?origins={s.get("latitude")},{s.get("longitude")}&destinations={d.get("latitude")},{d.get("longitude")}&key={GOOGLE_MAPS_API_KEY}'
    #         resp = requests.get(dm_url, timeout=10).json()
    #         gmaps_distance = None
    #         try:
    #             elems = resp.get('rows', [])[0].get('elements', [])
    #             if elems and elems[0].get('status') == 'OK':
    #                 meters = elems[0].get('distance', {}).get('value')
    #                 if meters is not None:
    #                     gmaps_distance = float(meters) / 1000.0
    #         except Exception:
    #             gmaps_distance = None
    # except Exception:
    #     gmaps_distance = None

    # return {'database_distance_km': db_distance, 'google_maps_distance_km': gmaps_distance}


# Serve frontend - mount static files AFTER all API routes
frontend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '.'))
if os.path.isdir(frontend_dir):
    @app.get("/")
    async def serve_root():
        index_path = os.path.join(frontend_dir, "index.html")
        if os.path.exists(index_path):
            return FileResponse(index_path)
        raise HTTPException(status_code=404, detail="index.html not found")
    
    # Mount static files for other assets (CSS, JS, images, etc.)
    app.mount("/", StaticFiles(directory=frontend_dir), name="static")
