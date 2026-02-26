# Charter Network Optimization

ILP-based optimizer for NCAA Division I athletic charter logistics. Minimizes ferry (deadhead) miles across a multi-conference, multi-sport charter network.

## Results (Feb 2026, Big Ten + SEC, MBB + WBB)

| Model | Monthly Ferry Cost | vs Baseline |
|---|---|---|
| Status Quo (Single Hub) | $4.0M | — |
| Nearest Base Selection | $2.1M | -47% |
| **Optimized (Multi-Base)** | **$1.3M** | **-68%** |

## Architecture

- **Ingest**: ESPN hidden API → game schedules → airport-mapped trips
- **Model**: Trip-based atomic units (tail locked for full away window)
- **Optimizer**: Integer Linear Programming via scipy/HiGHS
- **Viz**: Executive summary with side-by-side route maps

## Quick Start
pip install -e . python -m charternetwork.pipeline --conferences big_ten,sec --sports MBB,WBB
