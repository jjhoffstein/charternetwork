"""CEO-facing analytics: breakdowns, triangle routes, unit economics."""

from collections import defaultdict
import pandas as pd
from charternetwork.ingest import leg_dist


# ---------------------------------------------------------------------------
# T4.1 / T4.2: Per-conference and per-team breakdowns
# ---------------------------------------------------------------------------

def per_conference(trips, sol):
    "Breakdown of optimized ferry cost by conference"
    trip_map = {t.id: t for t in trips}
    # Allocate trip-to-trip arc costs 50/50 to each trip
    trip_cost = defaultdict(float)
    for tid, atype, arc in sol['selected']:
        if atype == 'trip':
            trip_cost[arc.from_trip] += arc.ferry_cost / 2
            trip_cost[arc.to_trip] += arc.ferry_cost / 2
        elif atype == 'depot_out' and arc.to_trip is not None:
            trip_cost[arc.to_trip] += arc.ferry_cost
        elif atype == 'depot_in' and arc.from_trip is not None:
            trip_cost[arc.from_trip] += arc.ferry_cost

    conf_stats = defaultdict(lambda: dict(trips=0, ferry_cost=0.0, total_nm=0.0))
    for t in trips:
        c = conf_stats[t.conf]
        c['trips'] += 1
        c['ferry_cost'] += trip_cost.get(t.id, 0.0)
        c['total_nm'] += t.dist_nm * 2  # round trip revenue miles
    return dict(conf_stats)


def per_team(trips, sol):
    "Breakdown of optimized ferry cost by team"
    trip_map = {t.id: t for t in trips}
    trip_cost = defaultdict(float)
    for tid, atype, arc in sol['selected']:
        if atype == 'trip':
            trip_cost[arc.from_trip] += arc.ferry_cost / 2
            trip_cost[arc.to_trip] += arc.ferry_cost / 2
        elif atype == 'depot_out' and arc.to_trip is not None:
            trip_cost[arc.to_trip] += arc.ferry_cost
        elif atype == 'depot_in' and arc.from_trip is not None:
            trip_cost[arc.from_trip] += arc.ferry_cost

    team_stats = defaultdict(lambda: dict(trips=0, ferry_cost=0.0, revenue_nm=0.0))
    for t in trips:
        s = team_stats[t.team]
        s['trips'] += 1
        s['ferry_cost'] += trip_cost.get(t.id, 0.0)
        s['revenue_nm'] += t.dist_nm * 2
    return dict(team_stats)


# ---------------------------------------------------------------------------
# T4.3: Unit economics
# ---------------------------------------------------------------------------

def unit_economics(trips, sol):
    "Key unit-level metrics"
    total_ferry_cost = sol['ferry_cost']
    total_revenue_nm = sum(t.dist_nm * 2 for t in trips)
    total_ferry_nm = sum(arc.ferry_nm for _, _, arc in sol['selected'])
    n_trips = len(trips)
    return dict(
        total_trips=n_trips,
        total_ferry_cost=total_ferry_cost,
        cost_per_trip=total_ferry_cost / n_trips if n_trips else 0,
        total_revenue_nm=total_revenue_nm,
        total_ferry_nm=total_ferry_nm,
        ferry_ratio=total_ferry_nm / total_revenue_nm if total_revenue_nm else 0,
        cost_per_ferry_nm=total_ferry_cost / total_ferry_nm if total_ferry_nm else 0,
    )


# ---------------------------------------------------------------------------
# T4.5: Triangle route extraction — the "aha moment"
# ---------------------------------------------------------------------------

def extract_chains(sol, trips):
    "Extract multi-trip chains from optimizer solution"
    trip_map = {t.id: t for t in trips}

    # Build adjacency: tail → ordered list of (from_trip, to_trip, arc)
    tail_chains = defaultdict(list)
    for tid, atype, arc in sol['selected']:
        if atype == 'trip':
            tail_chains[tid].append(arc)

    # For each tail, reconstruct the chain
    chains = []
    for tid, arcs in tail_chains.items():
        if not arcs:
            continue
        # Build from→to map
        fwd = {a.from_trip: a for a in arcs}
        # Find chain start (a from_trip that isn't anyone's to_trip)
        to_set = {a.to_trip for a in arcs}
        starts = [a.from_trip for a in arcs if a.from_trip not in to_set]
        for start in starts:
            chain_trips = [start]
            chain_arcs = []
            cur = start
            while cur in fwd:
                a = fwd[cur]
                chain_arcs.append(a)
                chain_trips.append(a.to_trip)
                cur = a.to_trip
            if len(chain_trips) >= 2:
                saved = sum(a.ferry_cost for a in chain_arcs)
                trip_objs = [trip_map[tid] for tid in chain_trips if tid in trip_map]
                chains.append(dict(
                    tail=tid,
                    trip_ids=chain_trips,
                    trips=trip_objs,
                    n_hops=len(chain_arcs),
                    ferry_cost=saved,
                    route=' → '.join(
                        f"{trip_map[tid].team} @ {trip_map[tid].game_apt}"
                        for tid in chain_trips if tid in trip_map),
                ))
    chains.sort(key=lambda c: c['n_hops'], reverse=True)
    return chains


def format_chain_narrative(chain):
    "Human-readable narrative for a multi-trip chain"
    trips = chain['trips']
    n = chain['n_hops'] + 1
    label = 'Triangle' if n == 3 else 'Daisy-Chain' if n >= 4 else 'Pair'
    lines = [f"🔗 {label} Route ({n} trips, tail {chain['tail']}):"]
    for i, t in enumerate(trips):
        lines.append(f"   {i+1}. {t.team} → {t.game_apt} ({t.game_dt.strftime('%b %d')})")
    lines.append(f"   Ferry cost for chain connections: ${chain['ferry_cost']:,.0f}")
    return '\n'.join(lines)


# ---------------------------------------------------------------------------
# T4.6: Export schedule as DataFrame
# ---------------------------------------------------------------------------

def schedule_df(sol, trips):
    "Optimized schedule as a DataFrame for CSV/Excel export"
    trip_map = {t.id: t for t in trips}
    rows = []
    for tid, atype, arc in sol['selected']:
        row = dict(tail=tid, arc_type=atype,
                   ferry_origin=arc.ferry_origin, ferry_dest=arc.ferry_dest,
                   ferry_nm=round(arc.ferry_nm, 1), ferry_hrs=round(arc.ferry_hrs, 2),
                   ferry_cost=round(arc.ferry_cost, 2))
        if arc.from_trip is not None and arc.from_trip in trip_map:
            t = trip_map[arc.from_trip]
            row.update(from_team=t.team, from_game_apt=t.game_apt,
                       from_game_dt=t.game_dt)
        if arc.to_trip is not None and arc.to_trip in trip_map:
            t = trip_map[arc.to_trip]
            row.update(to_team=t.team, to_game_apt=t.game_apt,
                       to_game_dt=t.game_dt)
        rows.append(row)
    return pd.DataFrame(rows)
