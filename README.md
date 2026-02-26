# Charter Network Optimization

> **Structural Alpha for Collegiate Athletics Charter Logistics**

An ILP-based optimizer that minimizes deadhead (ferry) miles across NCAA Division I
athletic charter networks. By treating each away trip as a locked atomic unit and solving
for globally optimal aircraft routing, the system recovers structural inefficiencies that
human brokers miss.

---

## Key Results (Feb 2026 — Big Ten + SEC, MBB + WBB)

| Strategy | Monthly Ferry Cost | vs Status Quo |
|---|---|---|
| Status Quo (Single Hub) | $4.0M | — |
| Nearest Base Selection | $2.1M | **-47%** |
| **ILP Optimized (Multi-Base)** | **$1.3M** | **-68%** |

The optimizer identifies **Triangle Routes** and **Daisy-Chains** between independent
trips — e.g. a tail finishing a Penn State drop-off in Philadelphia can pick up a Temple
outbound from the same airport instead of deadheading 600nm back to base.

---

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                        pipeline.py                          │
│  Orchestrates the full flow with CLI argument parsing       │
└──────┬──────────┬──────────┬──────────┬──────────┬──────────┘
       │          │          │          │          │
       ▼          ▼          ▼          ▼          ▼
  ┌────────┐ ┌────────┐ ┌────────┐ ┌────────┐ ┌────────────┐
  │ ingest │ │  legs  │ │  arcs  │ │optimize│ │  analytics │
  │        │ │        │ │        │ │        │ │            │
  │ESPN API│ │Outbound│ │Feasible│ │ ILP via│ │Breakdowns, │
  │→ games │ │+Return │ │connect-│ │ HiGHS  │ │chains, unit│
  │→ apts  │ │ pairs  │ │ ions   │ │        │ │ economics  │
  └────┬───┘ └────┬───┘ └────┬───┘ └────┬───┘ └─────┬──────┘
       │          │          │          │            │
       ▼          ▼          ▼          ▼            ▼
  ┌────────┐ ┌────────┐ ┌────────┐ ┌────────┐ ┌────────────┐
  │ config │ │ model  │ │baseline│ │  viz   │ │  viz_data  │
  │        │ │        │ │        │ │        │ │            │
  │Confs,  │ │Trip,   │ │Single- │ │US map, │ │Route line  │
  │aircraft│ │Tail,   │ │hub &   │ │exec    │ │generation  │
  │airports│ │Fleet,  │ │nearest │ │summary │ │& volumes   │
  │costs   │ │Arc     │ │base    │ │render  │ │            │
  └────────┘ └────────┘ └────────┘ └────────┘ └────────────┘
```

### Data Flow

1. **Ingest** — Pull game schedules from ESPN's hidden API for selected conferences/sports.
   Map venue cities to nearest IATA airports using OurAirports data + Nominatim geocoding.
2. **Legs** — For each away game, generate an outbound leg (depart 6h pre-game) and return
   leg (depart 4h post-game) with haversine distances.
3. **Model** — Bundle each outbound+return into an atomic **Trip**. The aircraft (tail) is
   locked for the full away window — no mid-trip swaps.
4. **Arcs** — For every pair of trips, check feasibility: capacity, max ferry distance
   (500nm default), time gap (48h default), crew duty limits (14h), and flight-time limits
   (10h). Generate depot-trip arcs for fleet base positioning.
5. **Optimize** — Solve the ILP: assign trips to tails minimizing total ferry cost (hourly
   rate + fuel burn). Constraints ensure every trip is covered exactly once, flow is
   conserved per tail, and depot departures/returns balance.
6. **Baseline** — Compute the two naive strategies (single-hub, nearest-base) using the
   same cost model for apples-to-apples comparison.
7. **Analytics** — Per-conference and per-team breakdowns, unit economics (cost/trip, ferry
   ratio), triangle route extraction with narratives, and full schedule CSV export.
8. **Viz** — Side-by-side US map with great-circle ferry routes for all three strategies +
   savings bar chart.

---

## The ILP Formulation

**Objective:** Minimize total ferry (deadhead) cost across all aircraft movements.

**Decision variables:** Binary — for each tail and each feasible arc (depot-to-trip,
trip-to-trip, trip-to-depot), is this arc used?

**Constraints:**
- **Coverage:** Every trip must be served by exactly one tail (via exactly one incoming arc).
- **Flow conservation:** For each tail at each trip node, inflow = outflow.
- **Depot balance:** Each tail must return to base the same number of times it departs.

**What makes it work:** The "Trip-Unit" constraint (the locked atomic away window)
dramatically reduces the solution space. Instead of routing individual flight legs, we
route *trips* — turning an intractable scheduling problem into a solvable network flow.

---

## Quick Start

```bash
# Install
git clone https://github.com/jjhoffstein/charternetwork.git
cd charternetwork
pip install -e ".[dev]"

# Run with defaults (Big Ten + SEC, MBB + WBB, full season)
python -m charternetwork

# Custom run
python -m charternetwork \\
    --conferences big_ten,sec,big_12 \\
    --sports MBB,WBB \\
    --start 20251101 \\
    --end 20260315 \\
    --bases '{"IND":2,"ORD":2,"DFW":1,"ATL":1}' \\
    --hub IND
```

### CLI Options

| Flag | Default | Description |
|------|---------|-------------|
| `--conferences` | `big_ten,sec` | Comma-separated conference keys |
| `--sports` | `MBB,WBB` | Comma-separated sport keys |
| `--start` | `20251101` | Season start (YYYYMMDD) |
| `--end` | `20260315` | Season end (YYYYMMDD) |
| `--bases` | `IND=2,ORD=2,DFW=1,ATL=1` | Fleet bases as JSON |
| `--aircraft` | `erj_145` | Aircraft type |
| `--hub` | `IND` | Single-hub baseline airport |
| `--max-ferry-nm` | `500` | Max ferry distance (nautical miles) |
| `--max-gap-hrs` | `48` | Max time gap between chainable trips |
| `--time-limit` | `300` | ILP solver time limit (seconds) |
| `--output` | `data/results/exec_summary.png` | Output path |

### Outputs

- `data/results/exec_summary.png` — Three-panel route map + savings chart
- `data/results/optimized_schedule.csv` — Full optimized schedule with tail assignments
- Console output — Unit economics, conference breakdowns, and top chain narratives

---

## Project Structure

```
charternetwork/
├── config.py        # Conferences, aircraft specs, airports, cost params
├── ingest.py        # ESPN API client, airport geocoding, haversine math
├── legs.py          # Away-game to outbound/return leg generation
├── model.py         # Core dataclasses: Trip, Tail, Fleet, Arc
├── arcs.py          # Feasibility checks + arc generation (duty/fuel aware)
├── baseline.py      # Naive strategy cost calculations
├── optimize.py      # ILP solver (scipy/HiGHS)
├── analytics.py     # Breakdowns, chains, unit economics, schedule export
├── viz.py           # Executive summary visualization
├── viz_data.py      # Route line + airport volume helpers
├── pipeline.py      # End-to-end orchestrator
└── __main__.py      # Entry point for python -m charternetwork
data/
├── geo/             # US states GeoJSON for map rendering
├── processed/       # Cached airport + team mappings
└── results/         # Generated outputs (PNG, CSV)
```

---

## Dependencies

**Core:** numpy, pandas, scipy, httpx, matplotlib

**Dev:** pytest

Python 3.11+ required. Solver is scipy's built-in HiGHS (no external solver install needed).

---

## License

See [LICENSE](LICENSE).
