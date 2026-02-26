import pandas as pd
from charternetwork.model import Arc, Trip, Tail
from charternetwork.ingest import leg_dist

def is_feasible(trip_a, trip_b, tail, apts, max_ferry_nm=500, max_gap_hrs=48):
    "Can a tail serve trip_b after completing trip_a?"
    if tail.capacity < max(trip_a.party_size, trip_b.party_size): return False
    ferry_nm = leg_dist(trip_a.home_apt, trip_b.home_apt, apts) if trip_a.home_apt != trip_b.home_apt else 0.0
    if ferry_nm > max_ferry_nm: return False
    f_hrs = ferry_nm / tail.cruise_kt
    earliest = trip_a.arrive_home + pd.Timedelta(hours=tail.turnaround_hrs + f_hrs)
    gap = (trip_b.depart_out - trip_a.arrive_home).total_seconds() / 3600
    if gap > max_gap_hrs: return False
    return earliest <= trip_b.depart_out

def make_arc(trip_a, trip_b, tail, apts):
    "Create arc from trip_a to trip_b"
    f_nm = leg_dist(trip_a.home_apt, trip_b.home_apt, apts) if trip_a.home_apt != trip_b.home_apt else 0.0
    f_hrs = f_nm / tail.cruise_kt
    return Arc(from_trip=trip_a.id, to_trip=trip_b.id, ferry_origin=trip_a.home_apt,
        ferry_dest=trip_b.home_apt, ferry_nm=f_nm, ferry_hrs=f_hrs, ferry_cost=f_hrs * tail.hourly_rate)

def depot_out(tail, trip, apts):
    "Arc from base to trip's team home airport"
    f_nm = leg_dist(tail.home_base, trip.home_apt, apts) if tail.home_base != trip.home_apt else 0.0
    f_hrs = f_nm / tail.cruise_kt
    return Arc(from_trip=None, to_trip=trip.id, ferry_origin=tail.home_base,
        ferry_dest=trip.home_apt, ferry_nm=f_nm, ferry_hrs=f_hrs, ferry_cost=f_hrs * tail.hourly_rate)

def depot_in(trip, tail, apts):
    "Arc from trip's team home airport back to base"
    f_nm = leg_dist(trip.home_apt, tail.home_base, apts) if trip.home_apt != tail.home_base else 0.0
    f_hrs = f_nm / tail.cruise_kt
    return Arc(from_trip=trip.id, to_trip=None, ferry_origin=trip.home_apt,
        ferry_dest=tail.home_base, ferry_nm=f_nm, ferry_hrs=f_hrs, ferry_cost=f_hrs * tail.hourly_rate)

def generate_arcs(trips, fleet, apts, max_ferry_nm=500, max_gap_hrs=48):
    "Generate all feasible arcs for the trip-based ILP"
    sorted_trips = sorted(trips, key=lambda t: t.depart_out)
    arcs = {}
    for tail in fleet:
        tarcs = []
        for t in sorted_trips:
            if tail.capacity >= t.party_size:
                tarcs.append(('depot_out', depot_out(tail, t, apts)))
                tarcs.append(('depot_in', depot_in(t, tail, apts)))
        for i, ta in enumerate(sorted_trips):
            for tb in sorted_trips[i+1:]:
                if (tb.depart_out - ta.arrive_home).total_seconds()/3600 > max_gap_hrs: break
                if is_feasible(ta, tb, tail, apts, max_ferry_nm, max_gap_hrs):
                    tarcs.append(('trip', make_arc(ta, tb, tail, apts)))
        arcs[tail.id] = tarcs
    total = sum(len(v) for v in arcs.values())
    print(f"Generated {total} arcs for {len(fleet)} tails across {len(trips)} trips")
    return arcs
