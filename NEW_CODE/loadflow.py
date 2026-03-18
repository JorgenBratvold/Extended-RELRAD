from copyreg import pickle
from turtle import left
import networkx as nx
import GraphSearch as gs
import numpy as np
import pandas as pd
from typing import Dict, List, Tuple
import plotting as pl
import pickle
import CreateSystem as cs

import warnings
warnings.filterwarnings("ignore", category=FutureWarning)
warnings.filterwarnings("ignore", category=pd.errors.SettingWithCopyWarning)



def lp_to_idx(bus):

    if isinstance(bus, int):
        return bus - 1 if bus > 0 else None

    bus = str(bus).strip()

    if bus.startswith("LP"):
        return int(bus.replace("LP", "")) - 1

    # external feeders
    if bus.startswith("BS") or bus.startswith("BB"):
        return None

    if bus.isdigit():
        val = int(bus)
        return val - 1 if val > 0 else None

    return None

def build_graph(sections, backupFeeders=None, with_section=False):
    G = nx.Graph()

    for sec, row in sections.iterrows():
        u = lp_to_idx(row["Upstream Bus"])
        v = lp_to_idx(row["Downstream Bus"])

        if None in (u, v):
            continue

        data = {"section": sec} if with_section else {}

        G.add_edge(u, v, **data)

    if backupFeeders is not None:
        for _, row in backupFeeders.iterrows():
            u = lp_to_idx(row["End 1"])
            v = lp_to_idx(row["End 2"])

            if None not in (u, v):
                G.add_edge(u, v, backup=True)

    return G

def build_section_switches(sections):

    switches = []

    for sec, row in sections.iterrows():

        u = lp_to_idx(row["Upstream Bus"])
        v = lp_to_idx(row["Downstream Bus"])

        if None in (u, v):
            continue

        direction = str(
            row.get("Disconnector direction", "N")
        ).strip().upper()

        if direction == "N":
            continue

        def add_switch(pos):
            switches.append({
                "u": u,
                "v": v,
                "type": "section",
                "name": sec,
                "status": "closed",
                "pos": pos,            
            })

        if direction == "U":
            add_switch("upstream")

        elif direction == "D":
            add_switch("downstream")

        elif direction == "B":
            add_switch("upstream")
            add_switch("downstream")
    return switches

def build_radial_trees_per_island(G_supply, sources):

    trees = []
    sources_set = set(sources)

    for comp in nx.connected_components(G_supply): 

        island_sources = sources_set.intersection(comp) 

        assert len(island_sources) == 1, \
            f"Island has {len(island_sources)} sources (expected 1)"

        root = next(iter(island_sources))

        T = nx.bfs_tree(G_supply.subgraph(comp), root).to_undirected()

        trees.append((T, root))

    return trees

def find_sources(buses, generationData):
    """
    Identify physical supply sources.
    """

    sources = []

    # filtrer kun main feeders
    main_feeders = generationData[
        generationData["Main Feeder"] == True
    ]

    for bus in main_feeders.index:

        idx = lp_to_idx(bus)
        if idx is not None:
            sources.append(idx)
    
    return sources

def reachable_nodes(G, sources):
    comps = nx.connected_components(G)
    return set().union(*(c for c in comps if any(s in c for s in sources)))

def connect_backup_feeders(
    G,
    reachable,
    backupFeeders,
    fault_component,
    switches,
):

    external_sources = []

    for i, bf in backupFeeders.iterrows():

        u = lp_to_idx(bf["End 1"])
        v = lp_to_idx(bf["End 2"])

        switch_info = {
            "u": u,
            "v": v,
            "type": "backup",
            "name": f"BF_{i}",
            "status": "open",
        }

        # Exteral feeder case
        if u is None or v is None:

            internal = u if u is not None else v

            if internal is None or internal not in G:
                switches.append(switch_info)
                continue

            if internal in reachable:
                print(f"External feeder at LP{internal+1} skipped (already energized)")
                switches.append(switch_info)
                continue

            # aldri energiser faultområde
            if internal in fault_component:
                print(f"Blocked external feeder at LP{internal+1}")
                switches.append(switch_info)
                continue

            print(f"External feeder energizes LP{internal+1}")

            switch_info["status"] = "closed"
            switches.append(switch_info)

            external_sources.append(internal)
            #reachable.add(internal)

            #reachable = reachable_nodes(G, reachable)
            continue


        powered_u = u in reachable # u er i en energisert del
        powered_v = v in reachable # v er i en energisert del

        if not (powered_u ^ powered_v):
            switches.append(switch_info)
            continue
            
        
        dead_node = v if powered_u else u # den som ikke er energisert
        dead_island = nx.node_connected_component(G, dead_node) # hele øya som er uten kraft

        if any(n in fault_component for n in dead_island):
            print(f"Blocked backfeed {u+1}-{v+1} (fault island)")
            switches.append(switch_info)
            continue

        if nx.has_path(G, u, v):
            switches.append(switch_info)
            continue

        print(f"Closing backup feeder: {u+1} <-> {v+1}")

        G.add_edge(u, v, backup=True)

        switch_info["status"] = "closed"
        switches.append(switch_info)

    return external_sources

def get_fault_edge_from_sections(sections, fault):

    row = sections.loc[fault]

    u = lp_to_idx(row["Upstream Bus"])
    v = lp_to_idx(row["Downstream Bus"])

    return (u, v)

def build_supply_trees(system, fault=None):

    sections_orig = system["sections"]
    buses_orig    = system["buses"]


    sections_copy = pickle.loads(pickle.dumps(system["sections"]))
    buses_copy    = pickle.loads(pickle.dumps(system["buses"]))

    generationData = system["generationData"]
    backupFeeders = system["backupFeeders"]

    G_all = build_graph(sections_orig, backupFeeders, with_section=True)

    switches = build_section_switches(sections_orig)

    fault_component = set()
    fault_edge = (None, None)
    disconnectors = []

    if fault is not None:

        fault_edge = get_fault_edge_from_sections(
            sections_orig, fault
        )

        buses, sections, disconnectors = gs.disconnect(
            fault,
            buses_copy,
            sections_copy,
        )

    else:
        sections = sections_orig
        buses = buses_orig


    for d in disconnectors:

        if not isinstance(d, dict):
            continue

        name = d.get("line")

        for sw in switches:
            if sw["type"] == "section" and sw["name"] == name:
                sw["status"] = "open"

    G = build_graph(sections)

    sources = find_sources(buses, generationData)
    print(sources)


    reachable = reachable_nodes(G, sources)

    if fault is not None and len(disconnectors) < 2:
        fault_component = set(G.nodes()) - reachable

    external_sources = connect_backup_feeders(
        G,
        reachable,
        backupFeeders,
        fault_component,
        switches,
    )

    sources.extend(external_sources)

    reachable = reachable_nodes(G, sources) # oppdater reachable etter å ha lagt til eksterne kilder

    G_supply = G.subgraph(reachable).copy() # subgraph med kun energiserte noder
    
    
    trees = build_radial_trees_per_island(G_supply, sources)
    print(f"Identified {len(trees)} supply trees")


    if fault_component:

        for sw in switches:

            if (
                sw["u"] in fault_component and
                sw["v"] in fault_component
            ):
                sw["status"] = "open"

    return trees, fault_edge, G_all, switches

class DLF_method:

    def __init__(self, Sbase, Vbase, include_shunt=True):

        self.Sbase = Sbase  # kVA
        self.Vbase = Vbase * 1e3  # V
        self.Zbase = (self.Vbase ** 2) / (Sbase * 1e3)
        self.Ibase = (Sbase * 1e3) / (np.sqrt(3) * self.Vbase)

        self.include_shunt = include_shunt

        self.buses: Dict[int, complex] = {}
        self.lines: List[Tuple[int, int, complex, complex]] = []
        self.slack = None

    def add_bus(self, bus_id, is_slack=False, S_load=0 + 0j):

        self.buses[bus_id] = -S_load
        if is_slack:
            self.slack = bus_id

    def add_line(self, from_bus, to_bus, z_pu, b_shunt=0.0):

        y_sh = 1j * b_shunt if b_shunt != 0 else 0.0
        self.lines.append((from_bus, to_bus, z_pu, y_sh))

    def build_system(self):

        for _, row in self.bus_df.iterrows():

            bus = int(row["Bus"])
            is_slack = bool(row["IsSlack"])
            P = float(row["P_pu (pu)"])
            Q = float(row["Q_pu (pu)"])

            if is_slack:
                self.add_bus(bus, is_slack=True)
            else:
                self.add_bus(bus, S_load=P + 1j * Q)

        if "Open" not in self.line_df.columns:
            self.line_df["Open"] = False

        # normalize Open column
        self.line_df["Open"] = (
            self.line_df["Open"]
            .astype(str)
            .str.strip()
            .str.lower()
            .map({"true": True, "false": False})
            .fillna(False)
        )


        lines_df = self.line_df[self.line_df["Open"] != True]

        for _, row in lines_df.iterrows():
        
            f = int(row["From"])
            t = int(row["To"])

            r = float(row["r_pu (pu)"])
            x = float(row["x_pu (pu)"])

            if self.include_shunt:
                b = float(row.get("b_pu (pu)", 0.0))
                self.add_line(f, t, r + 1j * x, b)
            else:
                self.add_line(f, t, r + 1j * x, 0.0)

        self._build_radial_structure()
        self._build_index_maps()

    def _build_radial_structure(self):

        G = nx.Graph()

        for f, t, z, y in self.lines:
            G.add_edge(f, t, impedance=z, y_sh=y)

        # BFS from slack
        tree = nx.bfs_tree(G, source=self.slack)

        new_lines = []
        parent_map = {}

        for node in tree.nodes:

            if node == self.slack:
                continue

            parent = list(tree.predecessors(node))[0]
            parent_map[node] = parent

            z = G[parent][node]["impedance"]
            y = G[parent][node]["y_sh"]

            new_lines.append((parent, node, z, y))

        if len(new_lines) != len(self.buses) - 1:
            raise ValueError("System is not radial!")

        self.lines = new_lines
        self.parent_map = parent_map

    def _build_index_maps(self):

        self.buses_sorted = sorted(self.buses.keys())
        self.non_slack_buses = [b for b in self.buses_sorted if b != self.slack]

        self.bus_index = {b: i for i, b in enumerate(self.buses_sorted)}
        self.line_index = {(f, t): i for i, (f, t, _, _) in enumerate(self.lines)}

        self.nbus = len(self.buses_sorted)
        self.nbranch = len(self.lines)

    def build_BIBC(self):

        N_branch = self.nbranch
        N_bus = self.nbus - 1

        bus_idx = {b: i for i, b in enumerate(self.non_slack_buses)}

        BIBC = np.zeros((N_branch, N_bus))

        for bus in self.non_slack_buses:

            col = bus_idx[bus]
            current = bus

            while current != self.slack:

                parent = self.parent_map[current]
                br = self.line_index[(parent, current)]

                BIBC[br, col] = 1
                current = parent

        self.BIBC = BIBC
        return BIBC

    def build_BCBV(self):

        N_branch = self.nbranch
        N_bus = self.nbus - 1

        bus_idx = {b: i for i, b in enumerate(self.non_slack_buses)}

        BCBV = np.zeros((N_bus, N_branch), dtype=complex)

        for bus in self.non_slack_buses:

            row = bus_idx[bus]
            current = bus

            while current != self.slack:

                parent = self.parent_map[current]
                br = self.line_index[(parent, current)]
                z = self.lines[br][2]

                BCBV[row, br] = z
                current = parent

        self.BCBV = BCBV
        return BCBV

    def build_DLF(self):

        self.build_BIBC()
        self.build_BCBV()
        self.DLF = self.BCBV @ self.BIBC
        return self.DLF

    def run_load_flow(self, tol=1e-8, max_iter=100):

        DLF = self.build_DLF()

        V = np.ones(self.nbus, dtype=complex)

        non_slack = self.non_slack_buses
        ns_idx = np.array([self.bus_index[b] for b in non_slack])

        S_load = np.array([self.buses[b] for b in non_slack], dtype=complex)

        for _ in range(max_iter):

            V_prev = V.copy()

            I = np.zeros(self.nbus, dtype=complex)
            I[ns_idx] = np.conj(S_load) / np.conj(V[ns_idx])

            dV = DLF @ I[ns_idx]

            V[ns_idx] = 1.0 + dV

            if np.max(np.abs(V - V_prev)) < tol:
                print(f"Converged in {_+1} iterations.")
                break

        self.Vfinal = V
        return V

class LinDistFlow_method(DLF_method):

    def run_load_flow(self):

        if not hasattr(self, "BIBC"):
            self.build_BIBC()

        T = self.BIBC

        non_slack = self.non_slack_buses
        ns_idx = np.array([self.bus_index[b] for b in non_slack])


        P = -np.array([self.buses[b].real for b in non_slack])
        Q = -np.array([self.buses[b].imag for b in non_slack])

        Pbr = T @ P
        Qbr = T @ Q

        R = np.array([z.real for _, _, z, _ in self.lines])
        X = np.array([z.imag for _, _, z, _ in self.lines])


        dV2 = T.T @ (-2 * (R * Pbr + X * Qbr))

        V2 = np.ones(self.nbus)
        V2[ns_idx] = 1.0 + dV2

        V = np.sqrt(np.maximum(V2, 0))

        self.Vfinal = V.astype(complex)

        return self.Vfinal

def build_loadflow_tables_from_tree(T, buses_lf, lines_lf):

    if "Open" not in lines_lf.columns:
        lines_lf["Open"] = False

    lines_lf["Open"] = (
        lines_lf["Open"]
        .astype(str)
        .str.strip()
        .str.lower()
        .map({"true": True, "false": False})
    )

    active_bus_ids = [n + 1 for n in T.nodes()]

    bus_table = buses_lf[
        buses_lf["Bus"].isin(active_bus_ids)
    ].copy()

    allowed_edges = set()

    for u, v in T.edges():
        allowed_edges.add((u+1, v+1))
        allowed_edges.add((v+1, u+1))

    edge_series = list(zip(lines_lf["From"], lines_lf["To"]))
    mask = pd.Series(edge_series).isin(allowed_edges)

    line_table = lines_lf[mask].copy()
    line_table["Open"] = False

    return bus_table, line_table

def run_loadflow_for_trees(trees, buses_lf, lines_lf, Sbase, Vbase):

    Vmag_total = {}
    print(f"Running load flow for {len(trees)} supply trees")
    for T, slack in trees:
        print(f"Running load flow for tree with slack at LP{slack+1}")

        bus_df, line_df = build_loadflow_tables_from_tree(T, buses_lf, lines_lf)


        bus_df["IsSlack"] = False
        bus_df.loc[bus_df["Bus"] == slack + 1,
                   "IsSlack"] = True


        #solver = DLF_method(Sbase, Vbase)
        solver = LinDistFlow_method(Sbase, Vbase)

        solver.bus_df = bus_df
        solver.line_df = line_df

        solver.build_system()
        V = solver.run_load_flow()

        for b in solver.buses_sorted:
            idx = solver.bus_index[b]
            Vmag_total[b - 1] = abs(V[idx])

    return Vmag_total

def run_simulation(system,
                   Sbase,
                   Vbase,
                   pos,
                   buses_lf,
                   lines_lf,
                   fault=None,
                   system_name=None):

    trees, fault_edge, G_all, all_switches  = \
        build_supply_trees(system, fault=fault)

    Vmag = run_loadflow_for_trees(
        trees,
        buses_lf,
        lines_lf,
        Sbase,
        Vbase
    )


    if len(trees) == 0:
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
        system_name=system_name,
        switches = all_switches
    )

    return Vmag, T_plot, fault_edge

def contingency_voltage_profiles(
    system,
    Sbase,
    Vbase,
    buses_lf: pd.DataFrame,
    lines_lf: pd.DataFrame,
    contingencies=None,
    system_name=None,
    include_basecase=True,
    group_tol=1e-6,
    figsize=(12, 6),
):
    """
    Plotter spenningsprofiler for hver unik contingency-gruppe.

    - En linje per unik spennings-tilstand
    - Legend viser hvilke contingencies som tilhører gruppen
    - Isolerte busser vises som brudd i linjen
    """

    import numpy as np
    import pandas as pd
    import matplotlib.pyplot as plt
    import networkx as nx

    # --------------------------------------------------
    # 1) Contingencies
    # --------------------------------------------------
    if contingencies is None:
        contingencies = list(system["sections"].index)

    cont_labels = []
    cont_faults = []

    if include_basecase:
        cont_labels.append("BASE")
        cont_faults.append(None)

    for c in contingencies:
        cont_labels.append(str(c))
        cont_faults.append(c)

    # --------------------------------------------------
    # 2) Bus ordering (radial/logisk!)
    # --------------------------------------------------
    G = build_graph(system["sections"])
    sources = find_sources(system["buses"], system["generationData"])

    if len(sources):
        root = sources[0]
        order = list(nx.bfs_tree(G, root).nodes())
        bus_ids_1based = [b + 1 for b in order]
    else:
        bus_ids_1based = sorted(buses_lf["Bus"].unique())

    bus_ids_1based = [
        b for b in bus_ids_1based
        if b in buses_lf["Bus"].values
    ]

    bus_ids_0based = [b - 1 for b in bus_ids_1based]

    # --------------------------------------------------
    # 3) Run contingencies
    # --------------------------------------------------
    results = []

    for label, fault in zip(cont_labels, cont_faults):

        print(f"Running contingency {label}")

        trees, _, _, _ = build_supply_trees(system, fault=fault)

        Vvec = np.full(len(bus_ids_0based), np.nan)

        if len(trees) > 0:
            Vmag = run_loadflow_for_trees(
                trees, buses_lf, lines_lf, Sbase, Vbase
            )

            for i, b0 in enumerate(bus_ids_0based):
                if b0 in Vmag:
                    Vvec[i] = Vmag[b0]

        results.append((label, Vvec))

    # --------------------------------------------------
    # 4) Group identical voltage states
    # --------------------------------------------------
    def same_voltage(a, b):
        mask = ~(np.isnan(a) & np.isnan(b))
        return np.allclose(a[mask], b[mask], atol=group_tol)

    groups = []

    for label, vec in results:

        placed = False

        for g in groups:
            if same_voltage(vec, g["V"]):
                g["members"].append(label)
                placed = True
                break

        if not placed:
            groups.append({
                "V": vec,
                "members": [label],
            })

    print(f"\nReduced {len(results)} contingencies → {len(groups)} groups")

    # --------------------------------------------------
    # 5) PUBLICATION-QUALITY VOLTAGE PROFILE
    # --------------------------------------------------
    fig, ax = plt.subplots(figsize=(12, 5))

    x = np.arange(len(bus_ids_1based))

    # stack voltages
    Vstack = np.vstack([g["V"] for g in groups])

    Vmin = np.nanmin(Vstack, axis=0)
    Vmax = np.nanmax(Vstack, axis=0)
    Vmean = np.nanmean(Vstack, axis=0)

    # --------------------------------------------------
    # Voltage operating region (MAIN MESSAGE)
    # --------------------------------------------------
    ax.fill_between(
        x,
        Vmin,
        Vmax,
        color="tab:blue",
        alpha=0.18,
        linewidth=0,
        label="Contingency operating range",
        zorder=1,
    )

    # --------------------------------------------------
    # Mean system behaviour
    # --------------------------------------------------
    ax.plot(
        x,
        Vmean,
        color="black",
        linestyle="--",
        linewidth=2.8,
        label="Mean voltage profile",
        zorder=3,
    )

    # --------------------------------------------------
    # Individual groups (secondary info)
    # --------------------------------------------------
    n_groups = len(groups)
    alpha_lines = min(0.9, max(0.35, 3 / n_groups))

    for i, g in enumerate(groups):

        ax.plot(
            x,
            g["V"],
            linewidth=1.4,
            alpha=alpha_lines,
            zorder=2,
        )

    # --------------------------------------------------
    # Voltage limits (industry standard)
    # --------------------------------------------------
    ax.axhline(0.95, linestyle=":", linewidth=1.5, color="red")
    ax.axhline(1.05, linestyle=":", linewidth=1.5, color="red")

    ax.text(
        0.99,
        0.952,
        "Voltage limits",
        transform=ax.get_yaxis_transform(),
        ha="right",
        fontsize=9,
        color="red",
    )

    # --------------------------------------------------
    # Axis styling
    # --------------------------------------------------
    ax.set_xlim(0, len(x)-1)
    ax.set_ylim(0.9, 1.01)

    ax.set_ylabel("Voltage magnitude |V| (pu)")
    ax.set_xlabel("Radial feeder distance (LP index)")

    ax.grid(True, alpha=0.25)

    title = "Voltage profiles under all contingencies"
    if system_name:
        title += f" — {system_name}"

    ax.set_title(title, fontsize=13, weight="bold")

    # fewer ticks but ALL LP still plotted
    step = max(1, len(x)//20)
    ax.set_xticks(x[::step])
    ax.set_xticklabels([f"LP{bus_ids_1based[i]}" for i in x[::step]])

    # --------------------------------------------------
    # CLEAN LEGEND
    # --------------------------------------------------
    ax.legend(
        loc="upper right",
        frameon=True,
        fontsize=10,
    )

    fig.tight_layout()
    plt.show()


    return groups, fig, ax


def export_contingency_results_to_excel(
    system,
    Sbase,
    Vbase,
    buses_lf,
    lines_lf,
    filename="contingency_results.xlsx",
    contingencies=None,
    include_basecase=True,
    group_tol=1e-6,
    undervoltage_limit=0.95,
):

    import numpy as np
    import pandas as pd
    import xlsxwriter

    # --------------------------------------------------
    # Contingency list
    # --------------------------------------------------
    if contingencies is None:
        contingencies = list(system["sections"].index)

    labels, faults = [], []

    if include_basecase:
        labels.append("BASE")
        faults.append(None)

    for c in contingencies:
        labels.append(str(c))
        faults.append(c)

    bus_ids = sorted(buses_lf["Bus"].astype(int).unique())
    bus_ids0 = [b - 1 for b in bus_ids]

    # --------------------------------------------------
    # Run loadflows
    # --------------------------------------------------
    voltage_results = {}

    for label, fault in zip(labels, faults):

        print(f"Running contingency {label}")

        trees, _, _, _ = build_supply_trees(system, fault=fault)

        V = np.full(len(bus_ids), np.nan)

        if len(trees):
            Vmag = run_loadflow_for_trees(
                trees, buses_lf, lines_lf, Sbase, Vbase
            )

            for i, b0 in enumerate(bus_ids0):
                if b0 in Vmag:
                    V[i] = Vmag[b0]

        voltage_results[label] = V

    # --------------------------------------------------
    # Group identical voltage profiles
    # --------------------------------------------------
    def same(a, b):
        mask = ~(np.isnan(a) & np.isnan(b))
        return np.allclose(a[mask], b[mask], atol=group_tol)

    groups = []

    for label, vec in voltage_results.items():

        placed = False
        for g in groups:
            if same(vec, g["V"]):
                g["members"].append(label)
                placed = True
                break

        if not placed:
            groups.append({"V": vec, "members": [label]})

    # --------------------------------------------------
    # Identify BASE group
    # --------------------------------------------------
    base_group = next(g for g in groups if "BASE" in g["members"])
    other_groups = [g for g in groups if g is not base_group]

    ordered_groups = [base_group] + other_groups

    # --------------------------------------------------
    # WRITE EXCEL (ONE SHEET)
    # --------------------------------------------------
    workbook = xlsxwriter.Workbook(filename)
    sheet = workbook.add_worksheet("Voltages")

    bold = workbook.add_format({"bold": True})
    red = workbook.add_format({"font_color": "red"})
    blue = workbook.add_format({
    "font_color": "blue"
    })
    

    # --------------------------------------------------
    # Headers
    # --------------------------------------------------
    sheet.write(0, 0, "Bus", bold)

    col = 1
    max_header_height = 1

    for i, g in enumerate(ordered_groups):

        title = "BASE" if i == 0 else f"G{i}"
        sheet.write(0, col, title, bold)

        # contingencies listed vertically
        for r, cont in enumerate(g["members"]):
            sheet.write(1 + r, col, cont)

        max_header_height = max(max_header_height,
                                1 + len(g["members"]))

        col += 1

    # --------------------------------------------------
    # Voltage rows (ALL START SAME HEIGHT)
    # --------------------------------------------------
    start_row = max_header_height + 1

    for r, bus in enumerate(bus_ids):

        sheet.write(start_row + r, 0, f"LP{bus}")

        for c, g in enumerate(ordered_groups, start=1):

            v = g["V"][r]

            if np.isfinite(v):
                sheet.write(start_row + r, c, float(v))
            else:
                sheet.write(start_row + r, c, "Isolated")

    # --------------------------------------------------
    # Conditional formatting
    # --------------------------------------------------
    sheet.conditional_format(
        start_row,
        1,
        start_row + len(bus_ids),
        len(ordered_groups),
        {
            "type": "cell",
            "criteria": "<",
            "value": undervoltage_limit,
            "format": red,
        },
    )

    sheet.conditional_format(
        start_row,
        1,
        start_row + len(bus_ids),
        len(ordered_groups),
        {
            "type": "cell",
            "criteria": "==",
            "value": '"Isolated"',
            "format": blue,
        },
    )

    left = workbook.add_format({"align": "left"})

    sheet.set_column(
        0,
        len(ordered_groups),
        14,
        left
    )


    workbook.close()


    print(f"\nExcel report written to: {filename}")



def print_switch_delimited_load_groups(system, fault=None):
    """
    Finds load groups that must be shed together based on
    topology and available switches.

    For each supply point:
        - removes controllable switches
        - computes connected downstream areas
        - prints shedding groups

    Parameters
    ----------
    system : RELRAD system dict
    fault : optional fault name
    """

    print("\n==============================")
    print("SWITCH-DELIMITED LOAD GROUPS")
    print("==============================")

    # ---- build post-fault topology exactly like simulation ----
    trees, fault_edge, G_all, switches = \
        build_supply_trees(system, fault=fault)

    if len(trees) == 0:
        print("No supplied areas.")
        return

    # controllable switch edges (closed ones define cut locations)
    switch_edges = set()

    for sw in switches:

        if sw["u"] is None or sw["v"] is None:
            continue

        # only switches that can isolate load areas
        if sw["type"] in ("section", "backup"):
            switch_edges.add((sw["u"], sw["v"]))
            switch_edges.add((sw["v"], sw["u"]))

    # ----------------------------------------------------------
    # process each supply tree independently
    # ----------------------------------------------------------
    for T, slack in trees:

        print(f"\nSupply point: LP{slack+1}")

        # copy tree
        G = T.copy()

        # remove switch edges → defines shedding boundaries
        for u, v in list(G.edges()):
            if (u, v) in switch_edges:
                G.remove_edge(u, v)

        # connected components = shedding groups
        groups = list(nx.connected_components(G))

        # sort groups by electrical distance (optional nice output)
        groups = sorted(groups, key=lambda g: min(g))

        print(f"Found {len(groups)} load groups:\n")

        for k, comp in enumerate(groups):

            buses = sorted([n+1 for n in comp])

            # mark slack group
            if slack in comp:
                tag = " (SUPPLY AREA — never shed)"
            else:
                tag = ""

            print(f"  Group {k:02d}: {buses}{tag}")

    print("\nDone.\n")

if __name__ == "__main__":


    #test_system = "NEW_CODE/new_systems/IEEE_123Bus.xlsx"
    test_system = "NEW_CODE/new_systems/IEEE_123Bus_external_backfeeds.xlsx"
    #test_system = "NEW_CODE/new_systems/CINELDI.xlsx"

    Vbase = {'NEW_CODE/new_systems/IEEE_123Bus.xlsx': 4.16, 'NEW_CODE/new_systems/IEEE_123Bus_external_backfeeds.xlsx': 4.16, 'NEW_CODE/new_systems/CINELDI.xlsx': 22.0} # kV
    Sbase = {'NEW_CODE/new_systems/IEEE_123Bus.xlsx': 100, 'NEW_CODE/new_systems/IEEE_123Bus_external_backfeeds.xlsx': 100, 'NEW_CODE/new_systems/CINELDI.xlsx': 10000} # kVA
    
    pos = pl.load_positions(test_system)

    system = cs.createSystem(test_system, LoadCurve=False)
    buses_lf = pd.read_excel(test_system, sheet_name="Buses")
    lines_lf = pd.read_excel(test_system, sheet_name="Lines")

    print_switch_delimited_load_groups(system, fault="S4")


#
#
##    groups, fig, ax = contingency_voltage_profiles(
##    system=system,
##    Sbase=Sbase[test_system],
##    Vbase=Vbase[test_system],
##    buses_lf=buses_lf,
##    lines_lf=lines_lf,
##    system_name="My Network"
##
##)
#
#    export_contingency_results_to_excel(
#    system=system,
#    Sbase=Sbase[test_system],
#    Vbase=Vbase[test_system],
#    buses_lf=buses_lf,
#    lines_lf=lines_lf,
#    filename="IEEE123_contingency_report.xlsx"
#)
#
#
#
#
#    
#