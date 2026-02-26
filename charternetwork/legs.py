import pandas as pd
from charternetwork.config import MIN_CHARTER_DIST_NM, PARTY_SIZE
from charternetwork.ingest import leg_dist

def derive_home_airports(df, airport_map):
    "Derive team→airport mapping from home game venues"
    home = df[~df.neutral].groupby('home').agg(city=('city','first'), state=('state','first')).reset_index()
    home['apt'] = home.apply(lambda r: airport_map.get((r.city, r.state)), axis=1)
    return dict(zip(home.home, home.apt))

def make_travel(df, team_apt, airport_map, apts):
    "Filter to away trips with mapped airports and distances"
    df = df.copy()
    df['origin'] = df['away'].map(team_apt)
    df['dest'] = df['airport']
    df = df[df.origin.notna() & df.dest.notna()].copy()
    df['dist_nm'] = [leg_dist(r.origin, r.dest, apts) for _, r in df.iterrows()]
    return df[df.dist_nm >= MIN_CHARTER_DIST_NM].copy()

def make_legs(travel):
    "Generate outbound and return legs from travel DataFrame"
    travel = travel.copy()
    travel['leg'] = 'outbound'
    if 'sport' in travel.columns: travel['party_size'] = travel['sport'].map(PARTY_SIZE)
    else: travel['party_size'] = PARTY_SIZE['MBB']
    ret = travel.copy()
    ret['leg'] = 'return'
    ret['origin'], ret['dest'] = ret['dest'].values, ret['origin'].values
    legs = pd.concat([travel, ret], ignore_index=True)
    legs['game_dt'] = pd.to_datetime(legs['date'])
    legs['depart_dt'] = legs['game_dt']
    legs.loc[legs.leg=='outbound', 'depart_dt'] -= pd.Timedelta(hours=6)
    legs.loc[legs.leg=='return', 'depart_dt'] += pd.Timedelta(hours=4)
    legs['arrive_dt'] = legs['depart_dt'] + pd.to_timedelta(legs['dist_nm']/250, unit='h')
    return legs

def build_dataset(df, apts, airport_map):
    "Full pipeline: games DataFrame → legs DataFrame"
    team_apt = derive_home_airports(df, airport_map)
    travel = make_travel(df, team_apt, airport_map, apts)
    return make_legs(travel), team_apt
