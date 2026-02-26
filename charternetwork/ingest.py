import numpy as np, httpx, time, json
import pandas as pd
from pathlib import Path
from charternetwork.config import AIRPORTS, SPORTS, CONFERENCES, MIN_CHARTER_DIST_NM

AIRPORTS_URL = 'https://davidmegginson.github.io/ourairports-data/airports.csv'
ESPN_BASE = 'https://site.api.espn.com/apis/site/v2/sports/basketball'

def haversine(lat1, lon1, lat2, lon2):
    "Great-circle distance in nautical miles"
    lat1, lon1, lat2, lon2 = map(np.radians, [lat1, lon1, lat2, lon2])
    dlat, dlon = lat2-lat1, lon2-lon1
    a = np.sin(dlat/2)**2 + np.cos(lat1)*np.cos(lat2)*np.sin(dlon/2)**2
    return 2 * 3440.065 * np.arcsin(np.sqrt(a))

def load_airport_coords():
    "Load IATA airport coordinates from OurAirports"
    apts = pd.read_csv(AIRPORTS_URL, usecols=['iata_code','latitude_deg','longitude_deg'])
    return apts.dropna(subset=['iata_code']).set_index('iata_code')

def leg_dist(orig, dest, apts):
    "Distance between two airport codes in nautical miles"
    o, d = apts.loc[orig], apts.loc[dest]
    return haversine(o.latitude_deg, o.longitude_deg, d.latitude_deg, d.longitude_deg)

def geocode(city, state):
    "Get lat/lon for a city via OpenStreetMap Nominatim"
    resp = httpx.get('https://nominatim.openstreetmap.org/search',
        params=dict(q=f'{city}, {state}', format='json', limit=1),
        headers={'User-Agent': 'charternetwork-research'})
    if resp.status_code == 200 and resp.json():
        r = resp.json()[0]
        return float(r['lat']), float(r['lon'])
    return None, None

def nearest_airport(lat, lon, apts):
    "Find nearest IATA airport to a lat/lon"
    dists = haversine(lat, lon, apts.latitude_deg.values, apts.longitude_deg.values)
    idx = np.argmin(dists)
    return apts.index[idx], round(dists[idx], 1)

def parse_event(e):
    "Extract key fields from an ESPN event"
    comp = e['competitions'][0]
    venue = comp['venue']['address']
    teams = {c['homeAway']: c['team']['displayName'] for c in comp['competitors']}
    return dict(date=e['date'], home=teams['home'], away=teams['away'],
                city=venue['city'], state=venue['state'], neutral=comp['neutralSite'])

def fetch_games(start, end, group=7, sport='mens-college-basketball'):
    "Fetch all games for a conference between start and end dates"
    from datetime import datetime, timedelta
    base = f'{ESPN_BASE}/{sport}/scoreboard'
    games, dt = [], datetime.strptime(start, '%Y%m%d')
    end_dt = datetime.strptime(end, '%Y%m%d')
    while dt <= end_dt:
        resp = httpx.get(base, params=dict(dates=dt.strftime('%Y%m%d'), groups=group, limit=50))
        if resp.status_code == 200:
            for e in resp.json().get('events', []): games.append(parse_event(e))
        dt += timedelta(days=1)
    return games

def map_airports(df, apts, airport_map=None):
    "Map city/state to airport codes, auto-geocoding unknown cities"
    if airport_map is None: airport_map = dict(AIRPORTS)
    missing = df[['city','state']].drop_duplicates()
    missing = missing[missing.apply(lambda r: (r.city, r.state) not in airport_map, axis=1)]
    for _, r in missing.iterrows():
        lat, lon = geocode(r.city, r.state)
        if lat is not None:
            code, _ = nearest_airport(lat, lon, apts)
            airport_map[(r.city, r.state)] = code
        time.sleep(1.1)
    df['airport'] = df.apply(lambda r: airport_map.get((r.city, r.state)), axis=1)
    return df, airport_map

def fetch_all(start, end, conferences=None, sports=None):
    "Fetch games for multiple conferences and sports"
    if conferences is None: conferences = CONFERENCES
    if sports is None: sports = SPORTS
    frames = []
    for cname, gid in conferences.items():
        for sname, sport in sports.items():
            games = fetch_games(start, end, group=gid, sport=sport)
            gdf = pd.DataFrame(games)
            if len(gdf) == 0: continue
            gdf['date'] = pd.to_datetime(gdf['date'])
            gdf['sport'], gdf['conf'] = sname, cname
            frames.append(gdf)
            print(f'{cname} {sname}: {len(gdf)} games')
    return pd.concat(frames, ignore_index=True)
