from charternetwork.ingest import leg_dist

def route_lines_naive(trips, base, apts):
    "Ferry lines for naive single-base model"
    lines = []
    for t in trips:
        if t.home_apt == base: continue
        o, d = apts.loc[base], apts.loc[t.home_apt]
        cost = leg_dist(base, t.home_apt, apts) * 2 / 250 * 3200
        lines.append(dict(lat1=o.latitude_deg, lon1=o.longitude_deg, lat2=d.latitude_deg, lon2=d.longitude_deg, cost=cost))
    return lines

def route_lines_nearest(trips, bases, apts):
    "Ferry lines for nearest-base model"
    lines = []
    for t in trips:
        best_base = min(bases, key=lambda b: leg_dist(b, t.home_apt, apts) if b != t.home_apt else 0)
        if best_base == t.home_apt: continue
        o, d = apts.loc[best_base], apts.loc[t.home_apt]
        cost = leg_dist(best_base, t.home_apt, apts) * 2 / 250 * 3200
        lines.append(dict(lat1=o.latitude_deg, lon1=o.longitude_deg, lat2=d.latitude_deg, lon2=d.longitude_deg, cost=cost))
    return lines

def route_lines_opt(sol, trips, apts):
    "Ferry lines for optimized solution"
    lines = []
    for tid, atype, arc in sol['selected']:
        if arc.ferry_nm < 1: continue
        o, d = apts.loc[arc.ferry_origin], apts.loc[arc.ferry_dest]
        lines.append(dict(lat1=o.latitude_deg, lon1=o.longitude_deg, lat2=d.latitude_deg, lon2=d.longitude_deg, cost=arc.ferry_cost, tail=tid, atype=atype))
    return lines

def airport_volumes(trips, apts):
    "Count trips per airport with coordinates"
    from collections import Counter
    counts = Counter()
    for t in trips: counts[t.home_apt] += 1; counts[t.game_apt] += 1
    return [dict(code=c, count=n, lat=apts.loc[c].latitude_deg, lon=apts.loc[c].longitude_deg) for c, n in counts.most_common() if c in apts.index]
