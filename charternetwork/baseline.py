from charternetwork.ingest import leg_dist

def naive_trip_cost_single(trips, base, apts, hourly_rate=3200, cruise_kt=250):
    "Baseline: each trip gets a dedicated tail from a single base"
    return sum((leg_dist(base, t.home_apt, apts) * 2 if base != t.home_apt else 0) / cruise_kt * hourly_rate for t in trips)

def naive_trip_cost_nearest(trips, bases, apts, hourly_rate=3200, cruise_kt=250):
    "Baseline: each trip gets the nearest base carrier"
    return sum(min(leg_dist(b, t.home_apt, apts) * 2 / cruise_kt * hourly_rate for b in bases) for t in trips)

def compare(trips, fleet, sol, bases, apts, hourly_rate=3200):
    "Full comparison table"
    n_single = naive_trip_cost_single(trips, fleet[0].home_base, apts, hourly_rate)
    n_nearest = naive_trip_cost_nearest(trips, bases, apts, hourly_rate)
    opt = sol['ferry_cost']
    return dict(naive_single=n_single, naive_nearest=n_nearest, optimized=opt,
        savings_vs_single=n_single-opt, savings_vs_nearest=n_nearest-opt,
        pct_vs_single=(1-opt/n_single)*100, pct_vs_nearest=(1-opt/n_nearest)*100)
