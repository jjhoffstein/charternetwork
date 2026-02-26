import numpy as np
from scipy.optimize import milp, LinearConstraint, Bounds
from scipy.sparse import lil_matrix

def solve(trips, fleet, arcs_dict, time_limit=300):
    "Solve the charter network ILP: assign trips to tails minimizing total ferry cost"
    trip_ids = sorted({t.id for t in trips})
    trip_idx = {tid: i for i, tid in enumerate(trip_ids)}
    tail_ids = sorted(arcs_dict.keys())
    n_trips, n_tails = len(trip_ids), len(tail_ids)

    var_list = [(tid, atype, arc) for tid, tarcs in arcs_dict.items() for atype, arc in tarcs]
    n_vars = len(var_list)

    c = np.array([arc.ferry_cost for _, _, arc in var_list])
    integrality = np.ones(n_vars)
    bounds = Bounds(lb=0, ub=1)
    constraints = []

    A_cov = lil_matrix((n_trips, n_vars))
    for j, (tid, atype, arc) in enumerate(var_list):
        if atype in ('depot_out', 'trip') and arc.to_trip is not None and arc.to_trip in trip_idx:
            A_cov[trip_idx[arc.to_trip], j] = 1
    constraints.append(LinearConstraint(A_cov.tocsr(), lb=1, ub=1))

    tail_idx = {tid: i for i, tid in enumerate(tail_ids)}
    A_flow = lil_matrix((n_tails * n_trips, n_vars))
    for j, (tid, atype, arc) in enumerate(var_list):
        ti = tail_idx[tid]
        if atype == 'depot_out' and arc.to_trip is not None and arc.to_trip in trip_idx:
            A_flow[ti*n_trips + trip_idx[arc.to_trip], j] += 1
        elif atype == 'depot_in' and arc.from_trip is not None and arc.from_trip in trip_idx:
            A_flow[ti*n_trips + trip_idx[arc.from_trip], j] -= 1
        elif atype == 'trip':
            if arc.to_trip is not None and arc.to_trip in trip_idx: A_flow[ti*n_trips + trip_idx[arc.to_trip], j] += 1
            if arc.from_trip is not None and arc.from_trip in trip_idx: A_flow[ti*n_trips + trip_idx[arc.from_trip], j] -= 1
    constraints.append(LinearConstraint(A_flow.tocsr(), lb=0, ub=0))

    A_bal = lil_matrix((n_tails, n_vars))
    for j, (tid, atype, arc) in enumerate(var_list):
        ti = tail_idx[tid]
        if atype == 'depot_out': A_bal[ti, j] = 1
        elif atype == 'depot_in': A_bal[ti, j] = -1
    constraints.append(LinearConstraint(A_bal.tocsr(), lb=0, ub=0))

    result = milp(c, integrality=integrality, bounds=bounds, constraints=constraints,
        options=dict(time_limit=time_limit))
    if not result.success: return None

    selected = [(tid, atype, arc) for (tid, atype, arc), x in zip(var_list, result.x) if x > 0.5]
    ferry_cost = sum(arc.ferry_cost for _, _, arc in selected)
    return dict(result=result, selected=selected, ferry_cost=ferry_cost, var_list=var_list)
