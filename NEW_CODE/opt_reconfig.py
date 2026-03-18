
# ============================================================
# optimization.py
# Switch-area optimal load shedding (RELRAD compatible)
# ============================================================

import pyomo.environ as pyo
import numpy as np
import networkx as nx
import loadflow as lf
import plotting as pl


def remove_shed_areas_from_tree(T, areas, z_values):
    """
    Physically removes shed areas from the supplied tree.

    Parameters
    ----------
    T : networkx.Graph
        supplied tree (0-based indexing)
    areas : dict[area_id -> set(nodes)]
    z_values : dict[area_id -> 0/1]

    Returns
    -------
    T_new : Graph
    """

    T_new = T.copy()

    nodes_to_remove = []

    for a, nodes in areas.items():
        if z_values.get(a, 0) > 0.5:
            nodes_to_remove.extend(nodes)

    T_new.remove_nodes_from(nodes_to_remove)

    return T_new


def extract_area_shedding(model):
    """
    Reads optimized shedding decisions.
    """
    z = {}

    for a in model.A:
        val = model.z[a].value
        z[a] = 0 if val is None else round(val)

    return z


# ============================================================
# BUILD SWITCH-DELIMITED AREAS
# ============================================================

def build_switch_areas(T, switches):
    """
    Build shedding areas separated by ALL switches (open or closed).
    Indices converted to 1-based to match lf_solver buses.
    """

    # convert tree to 1-based indexing
    T1 = nx.Graph()
    for u, v in T.edges():
        T1.add_edge(u + 1, v + 1)

    # remove every switch edge that exists in this tree
    for sw in switches:
        u = sw.get("u", None)
        v = sw.get("v", None)

        if u is None or v is None:
            continue

        u += 1
        v += 1

        if T1.has_edge(u, v):
            T1.remove_edge(u, v)

    comps = list(nx.connected_components(T1))

    areas = {}
    bus_area = {}

    for k, comp in enumerate(comps):
        areas[k] = set(comp)
        for b in comp:
            bus_area[b] = k

    return areas, bus_area


# ============================================================
# BUILD TREE OPF WITH GROUP SHEDDING
# ============================================================

def build_tree_opf_model(
    T,
    slack,      # <-- 1-based
    switches,
    bus_df,
    line_df,
    lf_solver,
    Vmin,
    Vmax,
):

    buses = lf_solver.buses_sorted
    parent_map = lf_solver.parent_map
    lines = [(p, c) for c, p in parent_map.items()]

    areas, bus_area = build_switch_areas(T, switches)

    # impedance maps
    zmap = {}
    for _, row in line_df.iterrows():
        a = int(row["From"])
        b = int(row["To"])
        zmap[frozenset((a, b))] = (float(row["r_pu (pu)"]), float(row["x_pu (pu)"]))

    r, x = {}, {}
    for i, j in lines:
        r[(i, j)], x[(i, j)] = zmap[frozenset((i, j))]

    # child structure
    children = {b: [] for b in buses}
    parent = {}
    for i, j in lines:
        parent[j] = i
        children[i].append(j)

    m = pyo.ConcreteModel()

    m.B = pyo.Set(initialize=buses)
    m.L = pyo.Set(initialize=lines)
    m.A = pyo.Set(initialize=list(areas.keys()))

    m.P = pyo.Var(m.L)
    m.Q = pyo.Var(m.L)
    m.v = pyo.Var(m.B)

    # ONE binary per area: 1 = shed whole area
    m.z = pyo.Var(m.A, domain=pyo.Binary)

    m.Pslack = pyo.Var()
    m.Qslack = pyo.Var()

    m.Pload = pyo.Param(m.B, mutable=True, initialize=0.0)
    m.Qload = pyo.Param(m.B, mutable=True, initialize=0.0)

    # slack voltage
    m.v[slack].fix(1.0)

    # ---- FIX: slack-area can NEVER be shed ----
    slack_area = bus_area[slack]
    m.z[slack_area].fix(0)

    # POWER BALANCE
    def balanceP(m, b):
        Pout = sum(m.P[(b, j)] for j in children[b])

        if b == slack:
            return m.Pslack - Pout == 0

        area = bus_area[b]
        Peff = (1 - m.z[area]) * m.Pload[b]
        return m.P[(parent[b], b)] - Pout == Peff

    def balanceQ(m, b):
        Qout = sum(m.Q[(b, j)] for j in children[b])

        if b == slack:
            return m.Qslack - Qout == 0

        area = bus_area[b]
        Qeff = (1 - m.z[area]) * m.Qload[b]
        return m.Q[(parent[b], b)] - Qout == Qeff

    m.balanceP = pyo.Constraint(m.B, rule=balanceP)
    m.balanceQ = pyo.Constraint(m.B, rule=balanceQ)

    # LINDISTFLOW vdrop
    def vdrop(m, i, j):
        return m.v[j] == m.v[i] - 2 * (r[(i, j)] * m.P[(i, j)] + x[(i, j)] * m.Q[(i, j)])

    m.vdrop = pyo.Constraint(m.L, rule=vdrop)

    # ---- FIX: apply voltage constraints only if area is energized ----
    # If z(area)=1 (shed), the constraint relaxes with big-M.
    MV = 10.0

    def vmin_rule(m, b):
        if b == slack:
            return pyo.Constraint.Skip
        a = bus_area[b]
        return m.v[b] >= Vmin**2 - MV * m.z[a]

    def vmax_rule(m, b):
        if b == slack:
            return pyo.Constraint.Skip
        a = bus_area[b]
        return m.v[b] <= Vmax**2 + MV * m.z[a]

    m.vmin = pyo.Constraint(m.B, rule=vmin_rule)
    m.vmax = pyo.Constraint(m.B, rule=vmax_rule)

    # OBJECTIVE (area shedding)
    m.obj = pyo.Objective(
        expr=sum(
            m.z[a] * sum(m.Pload[b] for b in areas[a] if b in m.B)
            for a in m.A
        ),
        sense=pyo.minimize,
    )

    return m, areas


# ============================================================
# SOLVE TREE OPF
# ============================================================

def solve_tree_opf(model, bus_df, solver):

    for _, r in bus_df.iterrows():

        b = int(r.Bus)

        P = float(r["P_pu (pu)"])
        pf = float(r.get("PowerFactor", 1.0))

        if pf >= 0.999:
            Q = 0.0
        else:
            phi = np.arccos(pf)
            Q = P * np.tan(phi)

        model.Pload[b].set_value(P)
        model.Qload[b].set_value(Q)

    results = solver.solve(model, tee=False)

    term = results.solver.termination_condition

    if term != pyo.TerminationCondition.optimal:
        return None

    z_values = extract_area_shedding(model)

    return z_values


# ============================================================
# RUN OPTIMIZED LOADFLOW
# ============================================================

def run_optimized_loadflow_for_trees(
        trees,
        switches,
        buses_lf,
        lines_lf,
        Sbase,
        Vbase,
        Vmin,
        Vmax):

    solver = pyo.SolverFactory("gurobi")

    Vmag_total = {}
    Shed_total = {}

    final_trees = []

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

        # ---------- BUILD OPF ----------
        model, areas = build_tree_opf_model(
            T,
            slack+1,
            switches,
            bus_df,
            line_df,
            lf_solver,
            Vmin,
            Vmax
        )

        z_values = solve_tree_opf(model, bus_df, solver)

        if z_values is None:
            final_trees.append((T, slack))
            continue

        # ---------- REMOVE SHED AREAS ----------
        T_new = remove_shed_areas_from_tree(
            T,
            areas,
            z_values
        )

        # keep only energized feeder
        T_new = keep_slack_component(T_new, slack)


        final_trees.append((T_new, slack))

        # store shed info
        for a, nodes in areas.items():
            if z_values[a] > 0.5:
                for n in nodes:
                    Shed_total[n] = 1.0

    # ---------- FINAL LOADFLOW ----------
    Vmag_total = {}

    for T_new, slack in final_trees:

        if len(T_new.nodes) == 0:
            continue

        # rebuild tables AFTER shedding
        bus_df, line_df = lf.build_loadflow_tables_from_tree(
            T_new,
            buses_lf,
            lines_lf
        )

        bus_df = bus_df.copy()
        bus_df["IsSlack"] = False
        bus_df.loc[bus_df["Bus"] == slack + 1, "IsSlack"] = True

        solver = lf.LinDistFlow_method(Sbase, Vbase)
        solver.bus_df = bus_df
        solver.line_df = line_df

        solver.build_system()
        V = solver.run_load_flow()

        for b in solver.buses_sorted:
            idx = solver.bus_index[b]
            Vmag_total[b - 1] = abs(V[idx])


    return Vmag_total, Shed_total, final_trees



def keep_slack_component(T, slack):
    """
    Keep only nodes electrically connected to slack.
    """

    if slack not in T:
        return nx.Graph()

    comp = nx.node_connected_component(T, slack)
    return T.subgraph(comp).copy()

# ============================================================
# MAIN ENTRY (USED BY YOUR SCRIPT)
# ============================================================

def run_simulation_optimized(
        system,
        Sbase,
        Vbase,
        pos,
        buses_lf,
        lines_lf,
        fault=None,
        system_name=None,
        Vmin=0.95,
        Vmax=1.05):

    trees, fault_edge, G_all, switches = \
        lf.build_supply_trees(system, fault=fault)

    Vmag, Shed, final_trees = \
        run_optimized_loadflow_for_trees(
            trees,
            switches,
            buses_lf,
            lines_lf,
            Sbase,
            Vbase,
            Vmin,
            Vmax
        )

    if len(final_trees) == 0:
        T_plot = nx.Graph()
    else:
        T_plot = nx.compose_all([T for T, _ in final_trees])

    pl.plot_post_fault_voltages(
        T_plot,
        fault_edge,
        Vmag,
        pos,
        G_all,
        bus_df=buses_lf,
        Shed=Shed,
        system_name=system_name,
        switches=switches
    )

    return Vmag, Shed, T_plot, fault_edge




import loadflow as lf
import CreateSystem as cs
import pandas as pd
import plotting as pl
import networkx as nx
import optimization as opt
import warnings
warnings.filterwarnings("ignore", category=FutureWarning)
warnings.filterwarnings("ignore", category=pd.errors.SettingWithCopyWarning)

if __name__ == "__main__":

    test_system = "NEW_CODE/new_systems/IEEE_123Bus.xlsx"
    #test_system = "NEW_CODE/new_systems/IEEE_123Bus_external_backfeeds.xlsx"
    #test_system = "NEW_CODE/new_systems/CINELDI.xlsx"

    Vbase = {'NEW_CODE/new_systems/IEEE_123Bus.xlsx': 4.16, 'NEW_CODE/new_systems/IEEE_123Bus_external_backfeeds.xlsx': 4.16, 'NEW_CODE/new_systems/CINELDI.xlsx': 22.0} # kV
    Sbase = {'NEW_CODE/new_systems/IEEE_123Bus.xlsx': 100, 'NEW_CODE/new_systems/IEEE_123Bus_external_backfeeds.xlsx': 100, 'NEW_CODE/new_systems/CINELDI.xlsx': 10000} # kVA
    
    pos = pl.load_positions(test_system)

    system = cs.createSystem(test_system, LoadCurve=False)
    buses_lf = pd.read_excel(test_system, sheet_name="Buses")
    lines_lf = pd.read_excel(test_system, sheet_name="Lines")

    fault = "S23"  # Example fault at bus S23

    lf.run_simulation(
        system,
        Sbase[test_system],
        Vbase[test_system],
        pos,
        buses_lf,
        lines_lf,
        system_name=test_system
    )

    lf.run_simulation(
        system,
        Sbase[test_system],
        Vbase[test_system],
        pos,
        buses_lf,
        lines_lf,
        fault=fault,
        system_name=test_system
    )

    # Optimized case
    #system = cs.createSystem(test_system, LoadCurve=False)
    run_simulation_optimized(
        system,
        Sbase[test_system],
        Vbase[test_system],
        pos,
        buses_lf,
        lines_lf,
        fault=fault,
        system_name=test_system,
        Vmin=0.95,
        Vmax=1.05
    )

