from charternetwork.ingest import leg_dist

def single_hub_cost(trips, base, apts, hourly_rate=3200, cruise_kt=250):
    "Baseline: each trip gets a dedicated tail from a single hub"
    return sum((leg_dist(base, t.home_apt, apts) * 2 if base != t.home_apt else 0) / cruise_kt * hourly_rate for t in trips)

def nearest_base_cost(trips, bases, apts, hourly_rate=3200, cruise_kt=250):
    "Baseline: each trip gets the nearest available base"
    return sum(min(leg_dist(b, t.home_apt, apts) * 2 / cruise_kt * hourly_rate for b in bases) for t in trips)

def compare(trips, sol, base, bases, apts, hourly_rate=3200):
    "Full comparison"
    sh = single_hub_cost(trips, base, apts, hourly_rate)
    nb = nearest_base_cost(trips, bases, apts, hourly_rate)
    opt = sol['ferry_cost']
    return dict(single_hub=sh, nearest_base=nb, optimized=opt,
        savings_vs_single=sh-opt, savings_vs_nearest=nb-opt,
        pct_vs_single=(1-opt/sh)*100, pct_vs_nearest=(1-opt/nb)*100)
