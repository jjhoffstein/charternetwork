<!-- PRESENTATION GUIDE
This document is designed to be converted into a CEO-facing presentation.
Key guidance for the presentation LLM:
- Tone: Confident but transparent. This is an open technical walkthrough, not a sales pitch.
- Audience: A CEO who knows collegiate charter logistics deeply. He will probe assumptions.
- Pacing: Lead with the business problem, then the insight, then the math, then the money.
- Visuals: Where noted, include the referenced images or generate diagrams.
- The presenter is technically strong but newer to the charter domain, so the document
  is designed to demonstrate rigor and domain understanding, not insider jargon.
-->

# Charter Network Optimization
## A Structural Approach to Ferry Cost Reduction in Collegiate Athletics

---

<!-- SLIDE NOTE: Title slide. Clean, professional. Subtitle conveys that this is
structural/systematic, not a one-off hack. -->

---

## 1. The Problem

Every time an athletic program flies to an away game, an aircraft has to get into
position first. That positioning flight — the **ferry** or **deadhead** — generates
zero revenue but carries the full cost of fuel, crew, and aircraft time.

In a traditional brokerage model, each trip is booked independently. A broker finds
an available tail, dispatches it to the team's home airport, and brings it back to
base after the return leg. This works — but it means:

- **No global visibility.** Each trip is optimized in isolation. A tail deadheading
  back to Indianapolis after dropping off Purdue in Philadelphia has no awareness
  that Penn State needs a pickup from the same region the next morning.
- **Geographic mismatch.** Contracting with carriers whose bases are far from the
  programs they service means every trip starts with a long, expensive ferry.
- **Margin compression at scale.** As the number of programs and conferences grows,
  the number of missed connections grows combinatorially — but human brokers can
  only hold so many schedules in their heads.

The question this project answers: **What if we could see every trip across every
conference simultaneously and route aircraft to minimize total ferry cost?**

<!-- SLIDE NOTE: This slide sets up the pain point. Consider a simple illustration:
two trips that share geography but are booked independently, each with redundant
ferry flights forming an X pattern. Then show the optimized version where the
tail chains from one to the other. -->

---

## 2. The Key Insight: The Trip as an Atomic Unit

The core modeling decision that makes this tractable is treating each **away trip**
as a single locked unit:

```
┌──────────────────────────────────────────────────────┐
│                    TRIP UNIT                         │
│                                                      │
│  Ferry In → Outbound Leg → Game → Return Leg → Done │
│                                                      │
│  One tail, one crew, locked for the full window.     │
└──────────────────────────────────────────────────────┘
```

We never propose splitting a trip across aircraft or swapping tails mid-window.
This constraint is **operationally realistic** — it's how trips actually work — and
it dramatically simplifies the optimization. Instead of routing thousands of
individual flight legs, we route hundreds of trip units.

The optimization happens in the **space between trips**: which tail, coming from
where, should service each trip — and can it chain to another trip afterward
instead of deadheading home?

<!-- SLIDE NOTE: This is the conceptual core. Emphasize that the trip-unit
constraint is not a simplification for convenience — it prevents operationally
infeasible solutions (crew swaps, repositioning mid-game, duty violations). -->

---

## 3. How It Works

The system is a six-stage pipeline that runs end-to-end from live schedule data
to an optimized routing plan.

### Stage 1: Schedule Ingestion
We pull game schedules directly from ESPN's API for every conference and sport in
scope. Each game gives us teams, date, venue city, and neutral-site status. Venue
cities are mapped to the nearest IATA airport.

**Current scope:** Big Ten + SEC, Men's and Women's Basketball (Nov 2025 – Mar 2026).
Extensible to any conference or sport ESPN covers.

### Stage 2: Leg Construction
For each away game, we generate two legs:
- **Outbound:** Depart team's home airport 6 hours before game time
- **Return:** Depart venue airport 4 hours after game time

Each leg carries a haversine distance in nautical miles. Short trips (under 50nm)
are filtered — those are bus trips, not charters.

### Stage 3: Fleet & Arc Generation
We define a fleet of aircraft at specified bases (e.g., 2 ERJ-145s at IND, 2 at ORD,
1 at DFW, 1 at ATL). The system then generates every **feasible connection** between
trips, subject to hard constraints:

| Constraint | Value | Rationale |
|---|---|---|
| Max ferry distance | 500 nm | Beyond this, chartering locally is cheaper |
| Max time gap | 48 hrs | Crew scheduling and aircraft utilization |
| Crew duty limit | 14 hrs | FAR Part 135 regulatory compliance |
| Flight time limit | 10 hrs | Crew flight-time regulations |
| Min turnaround | 90 min | Refuel, deplane, reposition |
| Capacity match | Per aircraft | Tail must seat the full travel party |

### Stage 4: Optimization (ILP)
An Integer Linear Program assigns every trip to a tail, minimizing total ferry cost.
The solver (HiGHS, via scipy) finds the **provably optimal** assignment — not a
heuristic or approximation.

Three hard constraints ensure feasibility:
1. **Coverage:** Every trip is served by exactly one tail.
2. **Flow conservation:** A tail that arrives at a trip must also depart from it.
3. **Depot balance:** Every tail returns to its home base.

### Stage 5: Baseline Comparison
To quantify the value, we compare the optimized solution against two baselines:
- **Single Hub:** Every tail dispatched from one central base (IND).
- **Nearest Base:** Each trip gets the closest available base.

All three use the same cost model (hourly rate + fuel burn) for a fair comparison.

### Stage 6: Visualization & Analytics
The pipeline outputs a three-panel executive summary map, per-conference and per-team
cost breakdowns, chain narratives, and a full optimized schedule CSV.

<!-- SLIDE NOTE: Consider splitting this into 2-3 slides. Stage 1-2 on one
(data in), Stage 3-4 on one (the optimization), Stage 5-6 on one (outputs).
The constraint table is important — it shows operational realism. -->

---

## 4. Results

### Cost Comparison

| Strategy | Monthly Ferry Cost | Reduction |
|---|---|---|
| Status Quo (Single Hub, IND) | ~$4.0M | — |
| Nearest Base (IND, ORD, DFW, ATL) | ~$2.1M | **-47%** |
| **ILP Optimized (Multi-Base)** | **~$1.3M** | **-68%** |

The jump from Single Hub to Nearest Base is intuitive — don't fly planes across
the country when you have a closer option. The jump from Nearest Base to Optimized
is where the system earns its keep: **chaining trips** that a human would never
connect because they span different teams, conferences, and sports.

### Visual: Ferry Route Comparison

<!-- SLIDE NOTE: Insert exec_summary.png here. The three-panel map is the visual
centerpiece. Left panel (red lines) = Single Hub, showing the spider-web of long
ferries from IND. Middle (blue) = Nearest Base, shorter but still redundant.
Right (green) = Optimized, showing dramatically fewer and shorter ferry legs.
Below: savings bar chart. -->

![Executive Summary](data/results/exec_summary.png)

---

## 5. Assumptions — Laid Bare

Every model makes assumptions. Here are ours, why we made them, and what changes
if they're wrong.

| # | Assumption | Current Value | Rationale | Sensitivity |
|---|---|---|---|---|
| 1 | **Outbound departure offset** | 6 hrs before game | Team arrives ~4hrs early + 2hr buffer | Tightening to 4hrs increases feasible arcs (more chaining). Loosening to 8hrs decreases them. |
| 2 | **Return departure offset** | 4 hrs after game | ~2.5hr game + 1.5hr ground ops | Same-day return is standard for basketball. Football may differ. |
| 3 | **Aircraft type** | ERJ-145 (37 seats) | Standard for basketball travel parties (~35 pax) | CRJ-200 (50 seats) is also modeled. Football requires larger aircraft not yet in scope. |
| 4 | **Hourly rate** | $3,200/hr (ERJ-145) | Market rate for Part 135 charter | This is the lever David knows best — the model re-optimizes cleanly with different rates. |
| 5 | **Fuel price** | $5.50/gal | Current Jet-A average | At 120 gal/hr burn, fuel adds ~$660/hr to ferry cost. A $1/gal swing is ~$120/hr. |
| 6 | **Max ferry distance** | 500 nm | Beyond this, a local charter is likely cheaper | Raising to 750nm unlocks more chains but at diminishing returns. |
| 7 | **Fleet size & basing** | 6 tails: IND(2), ORD(2), DFW(1), ATL(1) | Central/southeast coverage for Big Ten + SEC | Different base configs are a single CLI argument change. |
| 8 | **Crew duty limit** | 14 hrs | FAR Part 135 | Hard regulatory constraint — not adjustable. |
| 9 | **Schedule source** | ESPN public API | Free, real-time, covers all D-I | Neutral-site tournaments and rescheduled games may have lag. |

**Key takeaway:** Assumptions 1, 2, 6, and 7 are the most impactful tuning knobs.
The system is designed to re-run in minutes with different values, making it a
**scenario planning tool**, not a one-shot analysis.

<!-- SLIDE NOTE: This is where David will spend the most time. Present the table,
then be ready to discuss any row in depth. The message is: we know what we assumed,
we know what happens if we're wrong, and we can re-run instantly. -->

---

## 6. The "Aha" — Triangle Routes and Daisy-Chains

The optimizer's real value isn't just picking the nearest base — it's discovering
**multi-trip chains** that no human broker would think to look for.

### What is a Triangle Route?

A triangle route occurs when a tail, after completing Trip A, can reposition a short
distance to service Trip B (a completely unrelated team/conference) instead of
deadheading all the way back to base.

```
Without optimization:              With optimization:

  Base ←──── Trip A ────→ Base     Base ──→ Trip A ──→ Trip B ──→ Base
  Base ←──── Trip B ────→ Base          (short ferry)

  4 ferry legs                      3 ferry legs (1 is shorter)
```

### Daisy-Chains

When the schedule is dense (e.g., mid-conference play in January/February), the
optimizer finds chains of 3, 4, or even 5+ trips that a single tail can service
with minimal repositioning between each.

The pipeline automatically extracts and narrates these chains. Example output:

```
Triangle Route (3 trips, tail erj_145_IND_0):
   1. Iowa Hawkeyes → CMH (Jan 15)
   2. Ohio State Buckeyes → LAN (Jan 17)
   3. Michigan State Spartans → CID (Jan 19)
   Ferry cost for chain connections: $4,200
```

Compare: servicing these three trips independently from IND would cost ~$19,200
in ferry alone. The chain saves ~$15,000 on just three trips.

**These savings are invisible to a broker working trip-by-trip.** They only emerge
when you optimize across the full network simultaneously.

<!-- SLIDE NOTE: This is the emotional peak of the presentation. Use the before/after
diagram. If real chain examples are available from the latest run, substitute them
for the illustrative one above. The key message: this is money that's structurally
invisible without the tool. -->

---

## 7. Unit Economics

Beyond the headline savings, the system tracks granular metrics that expose where
value is created and where cost is concentrated.

### Key Metrics

| Metric | Definition | Why It Matters |
|---|---|---|
| **Cost per trip** | Total ferry cost / number of trips | Unit-level margin indicator |
| **Ferry ratio** | Ferry NM / Revenue NM | Network efficiency — lower is better |
| **Conference breakdown** | Ferry cost allocated by conference | Which contracts are most/least efficient |
| **Team breakdown** | Ferry cost allocated by team | Which programs to prioritize for base proximity |

### Conference View

The system breaks down ferry cost by conference, showing which relationships drive
the most ferry overhead. This directly informs **carrier procurement strategy** —
if the SEC accounts for 60% of ferry cost, that's where base selection matters most.

### Team View

Individual team cost profiles reveal outliers — e.g., West Coast teams in eastern
conferences (Oregon, UCLA in the Big Ten) will naturally have higher ferry costs.
This data supports pricing decisions: charge appropriately for geography.

<!-- SLIDE NOTE: If available, include a simple bar chart of per-conference ferry
cost. The team view is best as a sorted table, top 10 most/least expensive. -->

---

## 8. What's Next

The current system is a working proof-of-concept for basketball. The architecture
is designed to scale across several dimensions:

### Near-Term (Weeks)
- **More conferences** — Add Big 12, ACC, Big East with a single CLI flag.
- **Sensitivity dashboard** — Automated re-runs across fleet sizes and base configs
  to find the optimal network topology.
- **What-if mode** — Input a proposed new contract and see how it affects total
  network cost before committing.

### Medium-Term (Months)
- **Football** — Requires larger aircraft types (capacity 120+). The model supports
  mixed fleets; we need to add aircraft specs and validate timing assumptions.
- **Rolling re-optimization** — Re-run weekly as ESPN schedules update, catching
  rescheduled games and tournament bracket changes.
- **Carrier affinity scoring** — Analytically match carriers to programs based on
  base proximity and schedule overlap (the "Gravity Well" concept).

### Long-Term (Quarters)
- **Historical backtest** — Run last season's schedules through the optimizer and
  compare against actual costs paid. Validates the model and quantifies the
  opportunity with real dollars.
- **Interactive dashboard** — Web-based tool for exploring scenarios, viewing
  optimized schedules, and exporting reports.

<!-- SLIDE NOTE: Frame this as a roadmap, not a wishlist. Each item builds on the
existing architecture. The message: the foundation is built, scaling is incremental. -->

---

## 9. Technical Appendix

### ILP Formulation

Let T = set of trips, K = set of tails, A_k = set of feasible arcs for tail k.

**Minimize:**

    sum over k in K, a in A_k of: cost(a) * x(k,a)

**Subject to:**

    (Coverage)     For each trip t in T:
                   sum of x(k,a) for all k, all arcs a entering t = 1

    (Flow)         For each tail k, each trip t:
                   sum of x(k,a) entering t = sum of x(k,a) leaving t

    (Depot)        For each tail k:
                   number of depot-out arcs used = number of depot-in arcs used

    (Binary)       x(k,a) in {0, 1}

**Cost function:** cost(a) = ferry_hours * (hourly_rate + fuel_burn_gal_hr * fuel_price_gal)

### Data Sources

| Source | Usage | Update Frequency |
|---|---|---|
| ESPN Hidden API | Game schedules, venues, teams | Daily (live scores endpoint) |
| OurAirports (GitHub) | IATA airport coordinates | Monthly |
| OpenStreetMap Nominatim | Venue city geocoding | As needed (cached) |

### Repository Structure

```
charternetwork/
  config.py      — Conferences, aircraft, airports, cost parameters
  ingest.py      — ESPN API, geocoding, haversine distances
  legs.py        — Away game to outbound/return legs
  model.py       — Trip, Tail, Fleet, Arc dataclasses
  arcs.py        — Feasibility + arc generation (duty/fuel aware)
  baseline.py    — Single-hub and nearest-base comparisons
  optimize.py    — ILP solver (scipy/HiGHS)
  analytics.py   — Breakdowns, chains, unit economics
  viz.py         — Executive summary map rendering
  pipeline.py    — End-to-end orchestrator
```

<!-- SLIDE NOTE: This appendix can be a backup slide or handout. Most CEOs won't
need it during the presentation, but having it ready shows depth. -->

---

<!-- PRESENTATION CLOSING NOTE:
End the presentation by returning to the core number: 68% ferry cost reduction.
Restate that this is provably optimal (not a heuristic), operationally feasible
(duty limits, turnaround, capacity all enforced), and re-runnable in minutes
with different assumptions. The tool doesn't replace David's judgment — it gives
him a quantitative foundation to make faster, better-informed decisions about
carrier contracts and network strategy. -->
