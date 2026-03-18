import pyomo.environ as pyo
import numpy as np
from collections import defaultdict
import loadflow as lf
import networkx as nx
import plotting as pl


def build_tree_opf_model(lf_solver,
                         bus_df,
                         line_df,
                         Vmin=0.95,
                         Vmax=1.05):

    buses = lf_solver.buses_sorted
    slack = lf_solver.slack

    parent_map = lf_solver.parent_map
    lines = [(p, c) for c, p in parent_map.items()]

    parent = {}
    children = defaultdict(list)

    for i, j in lines:
        parent[j] = i
        children[i].append(j)

    for b in buses:
        children.setdefault(b, [])

    zmap = {}

    for _, row in line_df.iterrows():
        a = int(row["From"])
        b = int(row["To"])

        zmap[frozenset((a, b))] = (
            float(row["r_pu (pu)"]),
            float(row["x_pu (pu)"])
        )

    r = {}
    x = {}

    for i, j in lines:
        r[(i, j)], x[(i, j)] = zmap[frozenset((i, j))]

    m = pyo.ConcreteModel()

    m.B = pyo.Set(initialize=buses)
    m.L = pyo.Set(initialize=lines)

    # variables
    m.P = pyo.Var(m.L)
    m.Q = pyo.Var(m.L)
    m.v = pyo.Var(m.B)

    # binary load shedding (all-or-nothing)
    m.z = pyo.Var(m.B, domain=pyo.Binary)

    # slack injections
    m.Pslack = pyo.Var()
    m.Qslack = pyo.Var()

    # loads
    m.Pload = pyo.Param(m.B, mutable=True, initialize=0.0)
    m.Qload = pyo.Param(m.B, mutable=True, initialize=0.0)

    # alpha = Q/P (from power factor)
    m.alpha = pyo.Param(m.B, mutable=True, initialize=0.0)

    # slack voltage
    m.v[slack].fix(1.0)
    m.z[slack].fix(0)

    def balanceP(m, b):

        Pout = sum(m.P[(b, j)] for j in children[b])
        Peff = (1 - m.z[b]) * m.Pload[b]

        if b == slack:
            return m.Pslack - Pout == Peff

        return m.P[(parent[b], b)] - Pout == Peff

    def balanceQ(m, b):

        Qout = sum(m.Q[(b, j)] for j in children[b])
        Qeff = (1 - m.z[b]) * m.Qload[b]

        if b == slack:
            return m.Qslack - Qout == Qeff

        return m.Q[(parent[b], b)] - Qout == Qeff

    m.balanceP = pyo.Constraint(m.B, rule=balanceP)
    m.balanceQ = pyo.Constraint(m.B, rule=balanceQ)

    def vdrop(m, i, j):
        return m.v[j] == m.v[i] - 2 * (
            r[(i, j)] * m.P[(i, j)] +
            x[(i, j)] * m.Q[(i, j)]
        )

    m.vdrop = pyo.Constraint(m.L, rule=vdrop)

    m.vmin = pyo.Constraint(
        m.B,
        rule=lambda m, b: m.v[b] >= Vmin**2
    )

    m.vmax = pyo.Constraint(
        m.B,
        rule=lambda m, b: m.v[b] <= Vmax**2
    )

    # minimize shed active power
    m.obj = pyo.Objective(
        expr=sum(m.z[b] * m.Pload[b] for b in m.B)
    )

    return m

def solve_tree_opf(model, bus_df, solver):

    for _, r in bus_df.iterrows():

        b = int(r.Bus)

        P = float(r["P_pu (pu)"])
        pf = float(r.get("PowerFactor", 1.0))

        if pf >= 0.999:
            alpha = 0.0
            Q = 0.0
        else:
            phi = np.arccos(pf)
            alpha = np.tan(phi)
            Q = P * alpha

        model.Pload[b].set_value(P)
        model.Qload[b].set_value(Q)
        model.alpha[b].set_value(alpha)

    results = solver.solve(model, tee=False)

    term = results.solver.termination_condition

    if term not in (
        pyo.TerminationCondition.optimal,
        pyo.TerminationCondition.locallyOptimal,
    ):
        return None

    Vout = {
        b: np.sqrt(max(pyo.value(model.v[b]), 0.0))
        for b in model.B
    }

    Shed = {}
    for b in model.B:
        zb = model.z[b].value
        if zb is None:
            zb = 0.0
        Shed[b] = zb * pyo.value(model.Pload[b])

    return Vout, Shed

def voltage_violation_exists(Vmag,
                             Vmin=0.95,
                             Vmax=1.05):
    return any(
        (v < Vmin) or (v > Vmax)
        for v in Vmag.values()
    )

def run_optimized_loadflow_for_trees(
        trees,
        buses_lf,
        lines_lf,
        Sbase,
        Vbase,
        Vmin=0.95,
        Vmax=1.05):

    Vmag_total = {}
    Shed_total = {}
    solver = pyo.SolverFactory("gurobi")

    for T, slack in trees:

        bus_df, line_df = lf.build_loadflow_tables_from_tree(
            T, buses_lf, lines_lf
        )

        bus_df = bus_df.copy()
        bus_df["IsSlack"] = False
        bus_df.loc[bus_df["Bus"] == slack + 1, "IsSlack"] = True


        lf_solver = lf.LinDistFlow_method(Sbase, Vbase)
        lf_solver.bus_df = bus_df
        lf_solver.line_df = line_df

        lf_solver.build_system()
        V = lf_solver.run_load_flow()

        Vmag_tree = {
            b: abs(V[lf_solver.bus_index[b]])
            for b in lf_solver.buses_sorted
        }

        Vcorr = Vmag_tree
        Shed_tree = {}

        if voltage_violation_exists(Vmag_tree, Vmin, Vmax):
        
            print(f"Tree {slack+1}: running OPF")

            model = build_tree_opf_model(
                lf_solver,
                bus_df,
                line_df,
                Vmin,
                Vmax
            )

            result = solve_tree_opf(model, bus_df, solver)

            if result is None:
                print("OPF infeasible → fallback LinDistFlow")
                Shed_tree = {b: 0.0 for b in Vmag_tree}
            else:
                Vcorr, Shed_tree = result
                print(f"Shed tree: {Shed_tree}")



        for b, v in Vcorr.items():
            Vmag_total[b - 1] = v 

        if Shed_tree:
            for b, s in Shed_tree.items():
                Shed_total[b-1] = s

    return Vmag_total, Shed_total

def run_simulation_optimized(system,
                             Sbase,
                             Vbase,
                             pos,
                             buses_lf,
                             lines_lf,
                             fault=None,
                             system_name=None,
                             Vmin=0.95,
                             Vmax=1.05):

    trees, fault_edge, G_all, all_switches  = \
        lf.build_supply_trees(system, fault=fault)

    Vmag, Shed = run_optimized_loadflow_for_trees(
        trees,
        buses_lf,
        lines_lf,
        Sbase,
        Vbase,
        Vmin=Vmin,
        Vmax=Vmax
    )

    if len(trees) == 0:
        # no supplied network (blackout)
        T_plot = nx.Graph()
    else:
        T_plot = nx.compose_all([T for T, _ in trees])

    pl.plot_post_fault_voltages(
        T_plot,
        fault_edge,
        Vmag,
        pos,
        G_all,
        bus_df=buses_lf,
        Shed=Shed,
        system_name=system_name,
        switches=all_switches
    )

    return Vmag, Shed, T_plot, fault_edge

