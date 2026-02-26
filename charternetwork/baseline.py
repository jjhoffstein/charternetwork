from charternetwork.ingest import leg_dist
from charternetwork.config import FUEL_PRICE_GAL


def _ferry_round_trip_cost(base, home_apt, apts, hourly_rate, fuel_burn_gal_hr, cruise_kt):
    "Cost of a round-trip ferry: base → team home → base"
    if base == home_apt:
        return 0.0
    f_hrs = leg_dist(base, home_apt, apts) * 2 / cruise_kt
    return f_hrs * hourly_rate + f_hrs * fuel_burn_gal_hr * FUEL_PRICE_GAL


def single_hub_cost(trips, base, apts, hourly_rate=3200, fuel_burn_gal_hr=120, cruise_kt=250):
    "Baseline: each trip gets a dedicated tail from a single hub"
    return sum(_ferry_round_trip_cost(base, t.home_apt, apts, hourly_rate, fuel_burn_gal_hr, cruise_kt)
               for t in trips)


def nearest_base_cost(trips, bases, apts, hourly_rate=3200, fuel_burn_gal_hr=120, cruise_kt=250):
    "Baseline: each trip gets the nearest available base"
    return sum(
        min(_ferry_round_trip_cost(b, t.home_apt, apts, hourly_rate, fuel_burn_gal_hr, cruise_kt)
            for b in bases)
        for t in trips)


def compare(trips, sol, base, bases, apts, hourly_rate=3200, fuel_burn_gal_hr=120, cruise_kt=250):
    "Full comparison across all three models"
    sh = single_hub_cost(trips, base, apts, hourly_rate, fuel_burn_gal_hr, cruise_kt)
    nb = nearest_base_cost(trips, bases, apts, hourly_rate, fuel_burn_gal_hr, cruise_kt)
    opt = sol['ferry_cost']
    return dict(single_hub=sh, nearest_base=nb, optimized=opt,
        savings_vs_single=sh - opt, savings_vs_nearest=nb - opt,
        pct_vs_single=(1 - opt / sh) * 100 if sh > 0 else 0,
        pct_vs_nearest=(1 - opt / nb) * 100 if nb > 0 else 0)
