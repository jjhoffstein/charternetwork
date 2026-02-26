from dataclasses import dataclass, field
from typing import Optional
import pandas as pd

@dataclass
class Trip:
    "An away-game trip: outbound + idle + return as a locked unit"
    id: int
    team: str
    home_apt: str
    game_apt: str
    depart_out: pd.Timestamp
    arrive_game: pd.Timestamp
    game_dt: pd.Timestamp
    depart_ret: pd.Timestamp
    arrive_home: pd.Timestamp
    dist_nm: float
    party_size: int = 35
    sport: str = 'MBB'
    conf: str = ''

@dataclass
class Tail:
    "An aircraft available for charter"
    id: str
    aircraft_type: str
    capacity: int
    home_base: str
    hourly_rate: float
    cruise_kt: float = 250.0
    min_turnaround_min: int = 90

    @property
    def turnaround_hrs(self): return self.min_turnaround_min / 60

@dataclass
class Fleet:
    "Collection of tails"
    tails: list = field(default_factory=list)

    def __len__(self): return len(self.tails)
    def __iter__(self): return iter(self.tails)
    def __getitem__(self, i): return self.tails[i]

    @classmethod
    def uniform(cls, n, base, aircraft_type='erj_145', **kw):
        "Create n identical tails at the same base"
        from charternetwork.config import AIRCRAFT
        spec = AIRCRAFT[aircraft_type]
        tails = [Tail(id=f'{aircraft_type}_{i}', aircraft_type=aircraft_type, capacity=spec['capacity'],
            home_base=base, hourly_rate=spec['hourly_rate'], cruise_kt=spec['cruise_kt'],
            min_turnaround_min=spec['min_turnaround_min'], **kw) for i in range(n)]
        return cls(tails=tails)

    @classmethod
    def multi_base(cls, bases, aircraft_type='erj_145'):
        "Create tails across multiple bases: bases = dict(IND=3, ORD=2, ...)"
        from charternetwork.config import AIRCRAFT
        spec = AIRCRAFT[aircraft_type]
        tails = [Tail(id=f'{aircraft_type}_{base}_{i}', aircraft_type=aircraft_type, capacity=spec['capacity'],
            home_base=base, hourly_rate=spec['hourly_rate'], cruise_kt=spec['cruise_kt'],
            min_turnaround_min=spec['min_turnaround_min']) for base, n in bases.items() for i in range(n)]
        return cls(tails=tails)

@dataclass
class Arc:
    "A feasible connection between two trips (or depot)"
    from_trip: Optional[int]
    to_trip: Optional[int]
    ferry_origin: str
    ferry_dest: str
    ferry_nm: float
    ferry_hrs: float
    ferry_cost: float

def trips_from_df(df):
    "Convert travel DataFrame into Trip objects by pairing outbound/return"
    trips = []
    outbound = df[df.leg=='outbound'].reset_index(drop=True)
    for i, r in outbound.iterrows():
        cruise_hrs = r.dist_nm / 250
        trips.append(Trip(id=i, team=r.away, home_apt=r.origin, game_apt=r.dest, dist_nm=r.dist_nm,
            depart_out=r.depart_dt, arrive_game=r.depart_dt + pd.Timedelta(hours=cruise_hrs),
            game_dt=r.game_dt, depart_ret=r.game_dt + pd.Timedelta(hours=4),
            arrive_home=r.game_dt + pd.Timedelta(hours=4+cruise_hrs),
            party_size=getattr(r, 'party_size', 35),
            sport=getattr(r, 'sport', 'MBB'), conf=getattr(r, 'conf', '')))
    return trips
