"""End-to-end pipeline: ESPN ingest → ILP optimization → executive summary."""

import argparse, json, sys
from pathlib import Path

import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

from charternetwork.config import CONFERENCES, SPORTS
from charternetwork.ingest import load_airport_coords, fetch_all, map_airports
from charternetwork.legs import build_dataset
from charternetwork.model import trips_from_df, Fleet
from charternetwork.arcs import generate_arcs
from charternetwork.optimize import solve
from charternetwork.baseline import compare
from charternetwork.viz import exec_summary

DATA = Path(__file__).parent.parent / 'data'
DEFAULT_BASES = dict(IND=2, ORD=2, DFW=1, ATL=1)


def parse_args(argv=None):
    p = argparse.ArgumentParser(description='Charter Network Optimization Pipeline')
    p.add_argument('--conferences', default='big_ten,sec',
                   help='Comma-separated conference keys (default: big_ten,sec)')
    p.add_argument('--sports', default='MBB,WBB',
                   help='Comma-separated sport keys (default: MBB,WBB)')
    p.add_argument('--start', default='20251101', help='Season start YYYYMMDD')
    p.add_argument('--end', default='20260315', help='Season end YYYYMMDD')
    p.add_argument('--bases', default=None,
                   help='Fleet bases as JSON, e.g. \'{"IND":2,"ORD":2}\' (default: IND=2,ORD=2,DFW=1,ATL=1)')
    p.add_argument('--aircraft', default='erj_145', help='Aircraft type (default: erj_145)')
    p.add_argument('--hub', default='IND', help='Single-hub baseline airport (default: IND)')
    p.add_argument('--max-ferry-nm', type=int, default=500, help='Max ferry distance in NM')
    p.add_argument('--max-gap-hrs', type=int, default=48, help='Max gap between trips in hours')
    p.add_argument('--time-limit', type=int, default=300, help='ILP solver time limit in seconds')
    p.add_argument('--output', default=None, help='Output PNG path (default: data/results/exec_summary.png)')
    return p.parse_args(argv)


def run(args):
    confs = {k: CONFERENCES[k] for k in args.conferences.split(',')}
    sports = {k: SPORTS[k] for k in args.sports.split(',')}
    bases_dict = json.loads(args.bases) if args.bases else DEFAULT_BASES

    print(f"=== Charter Network Optimization ===")
    print(f"Conferences: {list(confs.keys())}")
    print(f"Sports:      {list(sports.keys())}")
    print(f"Period:      {args.start} -> {args.end}")
    print(f"Fleet bases: {bases_dict}")
    print()

    # 1. Load airport coordinates
    print("Loading airport coordinates...")
    apts = load_airport_coords()

    # 2. Fetch game schedules
    print("Fetching game schedules from ESPN...")
    games = fetch_all(args.start, args.end, conferences=confs, sports=sports)
    print(f"  -> {len(games)} games fetched\n")

    # 3. Map venues to airports
    print("Mapping venues to airports...")
    games, airport_map = map_airports(games, apts)
    print(f"  -> {games.airport.notna().sum()} games mapped\n")

    # 4. Build legs and trips
    print("Building travel legs...")
    legs, team_apt = build_dataset(games, apts, airport_map)
    print(f"  -> {len(legs)} legs ({len(legs)//2} round trips)\n")

    # 5. Convert to Trip objects
    trips = trips_from_df(legs)
    print(f"  -> {len(trips)} Trip objects\n")

    # 6. Create fleet
    print(f"Creating fleet: {args.aircraft} at {bases_dict}")
    fleet = Fleet.multi_base(bases_dict, aircraft_type=args.aircraft)
    print(f"  -> {len(fleet)} tails\n")

    # 7. Generate arcs
    print("Generating feasible arcs...")
    arcs = generate_arcs(trips, fleet, apts,
                         max_ferry_nm=args.max_ferry_nm,
                         max_gap_hrs=args.max_gap_hrs)

    # 8. Solve ILP
    print("\nSolving ILP...")
    sol = solve(trips, fleet, arcs, time_limit=args.time_limit)
    if sol is None:
        print("ERROR: Solver failed to find a feasible solution.")
        sys.exit(1)
    print(f"  -> Optimized ferry cost: ${sol['ferry_cost']:,.0f}\n")

    # 9. Compute baselines
    bases_list = list(bases_dict.keys())
    comp = compare(trips, sol, args.hub, bases_list, apts,
                   hourly_rate=fleet[0].hourly_rate)
    print(f"  Single hub ({args.hub}):  ${comp['single_hub']:,.0f}")
    print(f"  Nearest base:          ${comp['nearest_base']:,.0f}")
    print(f"  Optimized:             ${comp['optimized']:,.0f}")
    print(f"  Savings vs single hub: ${comp['savings_vs_single']:,.0f} ({comp['pct_vs_single']:.1f}%)")
    print(f"  Savings vs nearest:    ${comp['savings_vs_nearest']:,.0f} ({comp['pct_vs_nearest']:.1f}%)\n")

    # 10. Render executive summary
    print("Rendering executive summary...")
    fig = exec_summary(trips, sol, apts,
                       single_hub=comp['single_hub'],
                       nearest_base=comp['nearest_base'],
                       base=args.hub, bases=bases_list)

    out_path = args.output or str(DATA / 'results' / 'exec_summary.png')
    fig.savefig(out_path, dpi=150, bbox_inches='tight', facecolor=fig.get_facecolor())
    plt.close(fig)
    print(f"  -> Saved to {out_path}")
    print(f"\n=== Done ===")

    return dict(games=games, legs=legs, trips=trips, fleet=fleet,
                arcs=arcs, sol=sol, comp=comp)


def main(argv=None):
    args = parse_args(argv)
    return run(args)


if __name__ == '__main__':
    main()
