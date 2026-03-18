import math
import matplotlib.pyplot as plt
import pandas as pd
import copy
import numpy as np
from matplotlib.lines import Line2D

def build_network(excel_file, use_lambda_temp=False):

    buses_df = pd.read_excel(excel_file, "Buses") 
    lines_df = pd.read_excel(excel_file, "Lines")
    topology_df = pd.read_excel(excel_file, "Line Data")
    pos_df = pd.read_excel(excel_file, "Positions") if "Positions" in pd.ExcelFile(excel_file).sheet_names else None
    lp_df = pd.read_excel(excel_file, "Load Point Data")

    comp_df = pd.read_excel(
        excel_file,
        "Component Data",
        index_col=0 
    )

    network = {"buses": {}, "sections": {}, "positions": {}}

    for _, row in buses_df.iterrows():
        bid = int(row["Bus"]) - 1
        network["buses"][bid] = {
            "P_load": float(row["P_pu (pu)"]),
            "P": float(row["P_pu (pu)"]),
            "Q": float(row["Q_pu (pu)"]),
            "source": bool(row["IsSlack"]),
            "connected_sections": []
        }
    
    for i, (_, row) in enumerate(lp_df.iterrows()):
        network["buses"][i]["c1"] = float(row["c_NOK_per_kWh_1h"])
        network["buses"][i]["c4"] = float(row["c_NOK_per_kWh_4h"])

    for idx, topo in topology_df.iterrows():

        sid = idx + 1

        up = int(str(topo["Upstream Bus"]).replace("LP", "")) - 1
        down = int(str(topo["Downstream Bus"]).replace("LP", "")) - 1
        disc = str(topo["Disconnector direction"]).strip()
        breaker = str(topo["Fuse/breaker direction"]).strip()
        length = float(topo["Length"]) if not pd.isna(topo["Length"]) else 0.0

        assert disc in {"N", "U", "D", "B"}

        comp_name = f"Line{sid}"

        if comp_name not in comp_df.index:
            raise ValueError(f"{comp_name} not found in Component Data")

        comp = comp_df.loc[comp_name]

        # --- Sjekk hvilke kolonner som finnes ---
        has_temp = {"lambda_temp", "r_temp"}.issubset(comp.index)
        has_transformer = {"lambda_transformer", "r_transformer"}.issubset(comp.index)

        # --- Base verdier ---
        lambda_base = comp["lambda"] * length
        r_base = comp["r"]

        # --- Transformer (ALLTID med hvis finnes) ---
        lambda_transformer = comp["lambda_transformer"] if has_transformer else 0.0
        r_transformer = comp["r_transformer"] if has_transformer else 0.0

        # --- Temperatur (valgfritt) ---
        if use_lambda_temp and has_temp:
            lambda_temp = comp["lambda_temp"]
            r_temp = comp["r_temp"]
        else:
            lambda_temp = 0.0
            r_temp = 0.0

        # --- Total lambda ---
        lambda_total = lambda_base + lambda_temp + lambda_transformer

        # --- Vektet reparasjonstid ---
        if lambda_total > 0:
            repair_time = (
                lambda_base * r_base +
                lambda_temp * r_temp +
                lambda_transformer * r_transformer
            ) / lambda_total
        else:
            repair_time = 0.0

        network["sections"][sid] = {
            "up": up,
            "down": down,
            "r": float(lines_df.loc[idx, "r_pu (pu)"]),
            "x": float(lines_df.loc[idx, "x_pu (pu)"]),
            "disc": disc,
            "breaker": breaker,
            "fault": False,
            "lambda": float(lambda_total),
            "repair_time": float(repair_time),
            "switch_time": float(comp["s"]),
        }

        network["buses"][up]["connected_sections"].append(sid)
        network["buses"][down]["connected_sections"].append(sid)

    if pos_df is not None:
        network["positions"] = dict(
            zip(pos_df["Node"].astype(int) - 1,
                zip(pos_df["x"], pos_df["y"]))
        )

    lookup = {
    (u, v): sid
    for sid, s in network["sections"].items()
    for u, v in [(s["up"], s["down"]), (s["down"], s["up"])]
    }

    network["edge_lookup"] = lookup

    network["upstream_lookup"] = {
        s["down"]: sid
        for sid, s in network["sections"].items()
    }

    return network

def reset_and_apply_switches(network):

    LOAD_SCALE = 0.7803748480170235

    for bus in network["buses"].values():
        bus["P_load"] *= LOAD_SCALE
        bus["P"] *= LOAD_SCALE
        bus["Q"] *= LOAD_SCALE

    for sid, sec in network["sections"].items():

        if sid <= 3:
            continue

        sec["disc"] = "N"
        sec["switch_time"] = None
        sec["remote"] = False

        sec.pop("open_up", None)
        sec.pop("open_down", None)


    lookup = network["edge_lookup"]


    def set_switch(u, v, remote=False):

        u -= 1
        v -= 1

        sid = lookup.get((u, v)) or lookup.get((v, u))
        if sid is None:
            return

        sec = network["sections"][sid]

        up = sec["up"]
        down = sec["down"]

        # switch placed at first bus in tuple (Julia logic)
        if u == up:
            sec["disc"] = "U"
        elif u == down:
            sec["disc"] = "D"
        elif v == up:
            sec["disc"] = "U"
        elif v == down:
            sec["disc"] = "D"

        sec["switch_time"] = 1/3600 if remote else 0.5
        sec["remote"] = remote


    backup_switches = [

        (36,35),
        (62,61),
        (88,87)

    ]

    for u,v in backup_switches:
        set_switch(u,v,remote=False)


    remote_switches = [

        (33,26),
        (33,34),
        (33,37),
        (47,46),
        (47,49),
        (47,48),
        (86,85),
        (86,87),
        (86,89),
        (86,91),
        (86,92)
    ]

    for u,v in remote_switches:
        set_switch(u,v,remote=False)

    manual_switches = [

        (9,7),
        (9,12),
        (9,15),
        (9,13),
        (12,16),
        (12,26),

        (42,40),
        (42,43),
        (42,109),
        (42,44),

        (45,44),
        (45,116),
        (45,46),

        (71,70),
        (71,106),
        (71,72),

        (76,75),
        (76,102),
        (76,77),

    ]

    for u,v in manual_switches:
        set_switch(u,v,remote=False)


    return network

def trip_upstream_protection(fault_sid, sections, upstream_lookup):

    current_sid = fault_sid

    while current_sid is not None:

        sec = sections[current_sid]
        br = sec.get("breaker", "N")

        if br in ("U", "D", "B"):

            actions = {
                "U": ("open_up",),
                "D": ("open_down",),
                "B": ("open_up", "open_down"),
            }

            for key in actions[br]:
                sec[key] = True

            return current_sid

        current_sid = upstream_lookup.get(sec["up"])

    return None

def isolate_and_find_faulted_buses(sections, buses):

    fault_zone = set()
    boundary_edges = [] 

    fault_sid = next(
        sid for sid, sec in sections.items()
        if sec.get("fault", False)
    )

    sec_fault = sections[fault_sid]
    br = sec_fault.get("breaker", "N")
    disc = sec_fault.get("disc", "N")

    def dfs(bus):
        if bus in fault_zone:
            return

        fault_zone.add(bus)

        for sid in buses[bus]["connected_sections"]:
            sec = sections[sid]

            nbr = sec["down"] if sec["up"] == bus else sec["up"]

            if sec["disc"] == "N" and sec["breaker"] == "N":
                dfs(nbr)

            else:
                if nbr not in fault_zone:
                    boundary_edges.append((bus, sid))

    if disc == "B":
        sec_fault["open_up"] = True
        sec_fault["open_down"] = True
        return fault_zone

    if br == "U" and disc == "D":
        sec_fault["open_down"] = True
        return fault_zone


    start_buses = []
    if br == "U":
        start_buses.append(sec_fault["down"])
    elif br == "D":
        start_buses.append(sec_fault["up"])

    elif br == "N":
        if disc in ("N", "D"):
            start_buses.append(sec_fault["up"])
        if disc in ("N", "U"):
            start_buses.append(sec_fault["down"])

    for b in start_buses:
        dfs(b)

    for bus, sid in boundary_edges:
        sec = sections[sid]
        d = sec["disc"]

        if d == "U":
            sec["open_up"] = True
        elif d == "D":
            sec["open_down"] = True
        elif d == "B":
            if bus == sec["up"]:
                sec["open_up"] = True
            else:
                sec["open_down"] = True

    return fault_zone

def find_affected_buses(protection_sid, sections, buses):

    if protection_sid is None:
        return set(buses)

    sec = sections[protection_sid]
    br = sec.get("breaker", "N")

    if br == "D":
        root = sec["up"]
    elif br in ("U", "B"):
        root = sec["down"]
    else:
        return set(buses)

    affected = set()

    def dfs(b):
        if b in affected:
            return
        affected.add(b)

        for sid in buses[b]["connected_sections"]:
            if sid != protection_sid and sections[sid].get("breaker", "N") != "N":
                continue

            s = sections[sid]
            dfs(s["down"] if s["up"] == b else s["up"])

    dfs(root)
    return affected

def reclose_unused_protection(protection_sid, sections, fault_zone):

    if protection_sid is None:
        return

    sec = sections[protection_sid]

    if not (sec.get("open_up") or sec.get("open_down")) or sec.get("fault"):
        return

    if (sec["up"] in fault_zone) ^ (sec["down"] in fault_zone):
        return

    sec.pop("open_up", None)
    sec.pop("open_down", None)

def Reachable(root, buses, sections, fault_zone=None):

    energized = set()
    parent = {}
    children = {b: set() for b in buses}

    def dfs(bus, par=None):

        if bus in energized or (fault_zone is not None and bus in fault_zone):
            return

        energized.add(bus)

        if par is not None:
            parent[bus] = par
            children[par].add(bus)

        for sid in buses[bus]["connected_sections"]:
            s = sections[sid]

            d = s["disc"]
            if (
                (d == "U" and s.get("open_up", False)) or
                (d == "D" and s.get("open_down", False)) or
                (d == "B" and (
                    s.get("open_up", False) or
                    s.get("open_down", False)
                ))
            ):
                continue

            nxt_bus = s["down"] if s["up"] == bus else s["up"]

            dfs(nxt_bus, bus)

    dfs(root, None)

    return energized, parent, children

def backward_sweep(node, children, buses, P, Q):

    p_total = buses[node]["P"]
    q_total = buses[node]["Q"]

    for c in children[node]:
        pc, qc = backward_sweep(c, children, buses, P, Q)
        p_total += pc
        q_total += qc

    P[node] = p_total
    Q[node] = q_total

    return p_total, q_total

def forward_sweep(node, children, sections, edge_lookup, P, Q, V2):

    Vu2 = V2[node]

    for c in children[node]:

        sid = edge_lookup[(node, c)]
        s = sections[sid]

        drop = 2 * (s["r"] * P[c] + s["x"] * Q[c])
        V2[c] = max(Vu2 - drop, 0.0)

        forward_sweep(
            c, children, sections,
            edge_lookup, P, Q, V2
        )

def lindistflow(network, root, children, Vpre=None):

    P = {}
    Q = {}

    backward_sweep(root, children, network["buses"], P, Q)

    V2 = { root: (Vpre**2 if Vpre is not None else 1.0)}

    forward_sweep( root, children, network["sections"], network["edge_lookup"], P, Q, V2)

    return {n: math.sqrt(v) for n, v in V2.items()}, P, Q

def optimal_shedding_branch_bound3(
    network,
    root,
    children,
    parent,
    energized_buses,
    Vmin=None,
    Vpre=None,
    capacity=None,
    fault_zone=None,
):

    sections = network["sections"]
    buses = network["buses"]
    edge_lookup = network["edge_lookup"]

    best_shed = float("inf")
    best_sections_snapshot = None

    def capacity_ok(children_tree):

        if capacity is None:
            return True

        def subtree_load(n):

            P = buses[n]["P"]

            for c in children_tree[n]:
                P += subtree_load(c)

            return P

        total_load = subtree_load(root)

        return total_load <= capacity

    def build_candidates():

        def subtree(n):

            S = {n}

            for c in children[n]:
                S |= subtree(c)

            return S

        Candidates = {}

        for n, p in parent.items():

            sid = edge_lookup.get((p, n))

            d = sections[sid]["disc"] if sid else "N"

            if d != "N":

                T = subtree(n)

                Pc = sum(
                    buses[m]["P_load"] * buses[m].get("c4", 1)
                    for m in T
                )

                sec = sections[sid]

                if sec["disc"] == "U":
                    action_key = "open_up"

                elif sec["disc"] == "D":
                    action_key = "open_down"

                else:
                    action_key = (
                        "open_up"
                        if n == sec["up"]
                        else "open_down"
                    )

                Candidates[n] = {
                    "subtree": T,
                    "shed_cost": Pc,
                    "sid": sid,
                    "action_key": action_key,
                }

        sorted(
                Candidates,
                key=lambda x: Candidates[x]["shed_cost"],
                reverse=True,
            )

        return Candidates

    candidates = build_candidates()

    def apply_candidate_switching(selected):

        changes = []

        for g in selected:

            c = candidates[g]

            sec = sections[c["sid"]]

            key = c["action_key"]

            changes.append((sec, key, sec.get(key)))

            sec[key] = True

        return changes

    def undo_changes(changes):

        for sec, key, old in reversed(changes):

            if old is None:
                sec.pop(key, None)

            else:
                sec[key] = old

    def evaluate_configuration(candidate_set, require_energized=False):
        changes = apply_candidate_switching(candidate_set)
        test_energized, _, children_tree = Reachable(
            root,
            buses,
            sections,
            fault_zone=fault_zone,
        )
        feasible = True
        if require_energized and not test_energized:
            feasible = False
        if feasible and capacity is not None:
            if not capacity_ok(children_tree):
                feasible = False
        if feasible and Vmin is not None:
            V, Pflow, Qflow = lindistflow(
                network,
                root,
                children_tree,
                Vpre=Vpre,
            )
            if min(V.values()) < Vmin:
                feasible = False
        snapshot = None
        if feasible:
            snapshot = {
                sid: dict(sections[sid])
                for sid in sections
            }
        undo_changes(changes)
        return feasible, snapshot

    all_candidates = set(candidates.keys())
    
    feasible, _ = evaluate_configuration(all_candidates, require_energized=True)
    
    if not feasible:
        final_energized = set()
        shed_nodes = set(energized_buses)
        return final_energized, shed_nodes
    
    def search(remaining, selected, shedset):

        nonlocal best_shed
        nonlocal best_sections_snapshot

        current_shed = sum(
            candidates[g]["shed_cost"]
            for g in selected
        )

        if current_shed >= best_shed:
            return

        feasible, _ = evaluate_configuration(
            selected | set(remaining),
            require_energized=False,
        )

        if not feasible:
            return

        feasible, snapshot = evaluate_configuration(
            selected,
            require_energized=True,
        )

        if feasible:
            best_shed = current_shed
            best_sections_snapshot = snapshot
            return

        for i, g in enumerate(remaining):

            if candidates[g]["subtree"].issubset(
                shedset
            ):
                continue

            search(
                remaining[i + 1 :],
                selected | {g},
                shedset | candidates[g]["subtree"],
            )

    search(list(candidates.keys()), set(), set())

    if best_sections_snapshot:

        for sid in sections:

            sections[sid].clear()

            sections[sid].update(
                best_sections_snapshot[sid]
            )

    final_energized, parent, children = Reachable(
        root,
        buses,
        sections,
        fault_zone=fault_zone,
    )

    shed_nodes = set(energized_buses) - set(
        final_energized
    )

    return final_energized, shed_nodes

def compute_island_switch_time(island_buses, sections):

    if not island_buses:
        return 0.0

    Tmax = 0.0

    for sec in sections.values():

        d = sec["disc"]

        is_open = (
            (d == "U" and sec.get("open_up", False)) or
            (d == "D" and sec.get("open_down", False)) or
            (d == "B" and (
                sec.get("open_up", False) or
                sec.get("open_down", False)
            )))
        
        if not is_open:
            continue

        if sec["up"] in island_buses or sec["down"] in island_buses:
            Tmax = max(Tmax, float(sec["switch_time"]))

    return Tmax

def run_contingency_engine(
    sid,
    network,
    roots,
    Vmin,
    Sbase,
    cap_limit,
    V0,
    bess_buses=None,
    build_results=False,
):

    buses = network["buses"]
    sections = network["sections"]
    edge_lookup = network["edge_lookup"]

    sec = copy.deepcopy(sections)

    # reset state
    for s in sec.values():
        s["fault"] = False
        s.pop("open_up", None)
        s.pop("open_down", None)

    sec[sid]["fault"] = True

    lam = sec[sid]["lambda"]
    Trep = sec[sid]["repair_time"]

    # ---------------- PROTECTION ----------------
    pr_sid = trip_upstream_protection(sid, sec, network["upstream_lookup"])

    feeder = find_affected_buses(pr_sid, sec, buses)

    fz = isolate_and_find_faulted_buses(sec, buses)
    
    reclose_unused_protection(pr_sid, sec, fz)

    supplied = set()
    shed = set()
    t_switch = {}
    owner = {}

    buses_tmp = copy.deepcopy(buses)

    # ---------------- RESTORATION ----------------
    for root in roots:

        for b in buses_tmp:
            buses_tmp[b]["P"] = buses[b]["P"]

        E, parent, children = Reachable(root, buses_tmp, sec, fz)
        E-=supplied

        if not E:
            continue

        if bess_buses:
            for b in E:
                if (b + 1) in bess_buses:
                    buses_tmp[b]["P"] -= bess_buses[b + 1]["P"]

        case = {
            "buses": buses_tmp,
            "sections": sec,
            "edge_lookup": edge_lookup
        }

        cap = 1000 if root == roots[0] else cap_limit

        E_final, shed_part = optimal_shedding_branch_bound3(
            network=case,
            root=root,
            children=children,
            parent=parent,
            energized_buses=E,
            Vmin=Vmin,
            Vpre=V0.get(root, 1.0),
            capacity=cap,
            fault_zone=fz
        )

        E_final = set(E_final)
        supplied |= E_final

        if shed_part:
            shed |= set(shed_part)
            shed-=E_final

        T = compute_island_switch_time(E_final, sec)

        for b in E_final:
            t_switch[b] = T
            owner[b] = root

    # ---------------- ENS ----------------
    ENS_contrib = {}

    for b in feeder:

        P = max(buses[b]["P"], 0) * Sbase

        if b in fz:
            ENS_contrib[b] = lam * Trep * P
        elif b in supplied:
            ENS_contrib[b] = lam * t_switch.get(b, 0) * P
        else:
            ENS_contrib[b] = lam * Trep * P

    # ---------------- OPTIONAL RESULTS ----------------
    result = None

    bess_power = {}
    if build_results:

        buses_final = copy.deepcopy(buses)

        if bess_buses:
            for b in supplied:
                if (b + 1) in bess_buses:
                    buses_final[b]["P"] -= bess_buses[b + 1]["P"]
                    bess_power[b] = bess_buses[b + 1]["P"]

        V_after, P_after, Q_after, parent_after = {}, {}, {}, {}

        for root in roots:

            E, parent, children = Reachable(root, buses_final, sec, fz)
            E = {b for b in E if owner.get(b) == root}

            if not E:
                continue

            V, P, Q = lindistflow(
                {
                    "buses": buses_final,
                    "sections": sec,
                    "edge_lookup": edge_lookup
                },
                root,
                children,
                Vpre=V0.get(root, 1.0)
            )

            V_after.update(V)
            P_after.update(P)
            Q_after.update(Q)
            parent_after.update(parent)

        result = {
            "sections": sec,
            "voltages": V_after,
            "Pflows": P_after,
            "Qflows": Q_after,
            "energized_buses": supplied,
            "shed_nodes": shed,
            "switching_owner": owner,
            "roots": roots,
            "bess_buses": bess_buses or {},
            "bess_power": bess_power or {},
            "fault_zone": fz,
            "parent": parent_after
        }

    return ENS_contrib, result

def run_analytical(network, roots, Vmin, Sbase, cap_limit):

    buses = network["buses"]
    roots = [r - 1 for r in roots]

    # prefault
    _, _, tree = Reachable(roots[0], buses, network["sections"])
    V0, _, _ = lindistflow(network, roots[0], tree)

    ENS = {b: 0.0 for b in buses}

    for sid in network["sections"]:

        contrib, _ = run_contingency_engine(
            sid,
            network,
            roots,
            Vmin,
            Sbase,
            cap_limit,
            V0,
            build_results=False
        )

        for b, val in contrib.items():
            ENS[b] += val

    return ENS

def run_analytical_pipeline(
    network,
    roots,
    Vmin,
    Sbase,
    cap_limit,
    contingency_sid=None,
    bess_buses=None,
):

    buses = network["buses"]
    roots = [r - 1 for r in roots]

    # prefault
    _, _, tree = Reachable(roots[0], buses, network["sections"])
    V0, _, _ = lindistflow(network, roots[0], tree)

    ENS = {b: 0.0 for b in buses}
    results = {}

    sids = [contingency_sid] if contingency_sid else network["sections"].keys()

    for sid in sids:

        contrib, res = run_contingency_engine(
            sid,
            network,
            roots,
            Vmin,
            Sbase,
            cap_limit,
            V0,
            bess_buses=bess_buses,
            build_results=True
        )

        for b, val in contrib.items():
            ENS[b] += val

        results[sid] = res

    return ENS, results

def plot_network(
    pos,
    sections,
    voltages,
    energized_buses,
    buses,
    switching_owner=None,
    shed_nodes=None,
    roots=None,
    bess_power=None,
    Pflows=None,
    parent=None,
    Sbase=1,
    show=False,
):

    bess_power = bess_power or {}
    shed_nodes = set(shed_nodes or [])
    roots = set(roots or [])
    energized_buses = set(energized_buses)
    switching_owner = switching_owner or {}

    fig, ax = plt.subplots(figsize=(15, 9))
    used_boxes = []

    LINE_COLOR = "#2c2c2c"
    SWITCH_OPEN = "#d62728"
    SWITCH_CLOSED = "#FEFAFA"

    ROOT_COLOR = "#1870d3"
    ENERGIZED_COLOR = "#4ae27a"
    SHED_COLOR = "#ff9f1c"
    ISO_COLOR = "#878383"
    DG_COLOR = "#b07cff"

    BUS_EDGE = "black"
    FAULT_COLOR = "red"

    # -------------------------------------------------
    # PRECOMPUTE GEOMETRY (major speedup)
    # -------------------------------------------------
    valid_sections = []
    line_segments = []
    switch_points = []

    for s in sections.values():
        up = s["up"]
        down = s["down"]

        if up not in pos or down not in pos:
            continue

        p1 = np.asarray(pos[up], dtype=float)
        p2 = np.asarray(pos[down], dtype=float)

        vec = p2 - p1
        L = np.linalg.norm(vec)
        if L == 0:
            continue

        v = vec / L
        AB = vec
        denom = float(np.dot(AB, AB))

        sec_geom = {
            "section": s,
            "p1": p1,
            "p2": p2,
            "v": v,
            "A": p1,
            "B": p2,
            "AB": AB,
            "denom": denom,
        }
        valid_sections.append(sec_geom)
        line_segments.append((p1, p2, AB, denom))

        disc = s["disc"]
        if disc in ("U", "B"):
            switch_points.append(p1 + 0.6 * v)
        if disc in ("D", "B"):
            switch_points.append(p2 - 0.6 * v)

    node_points = np.array(list(pos.values()), dtype=float) if pos else np.empty((0, 2), dtype=float)
    switch_points_arr = np.array(switch_points, dtype=float) if switch_points else np.empty((0, 2), dtype=float)

    # fixed candidate angles exactly as before
    angles = np.linspace(0, 2 * np.pi, 12, endpoint=False)
    base_radius = 1.3
    vertical_shrink = 0.25
    cos_a = np.cos(angles)
    sin_a = np.sin(angles)
    radii = base_radius - vertical_shrink * (sin_a ** 2)

    def place_text_smart(ax, x, y, text, used_boxes, fontsize=6):
        candidates = np.column_stack((
            x + radii * cos_a,
            y + radii * sin_a
        ))  # shape (12, 2)

        clearance = np.full(len(candidates), np.inf, dtype=float)

        # distance to all buses
        if node_points.size:
            d_nodes = np.sqrt(((candidates[:, None, :] - node_points[None, :, :]) ** 2).sum(axis=2))
            clearance = np.minimum(clearance, d_nodes.min(axis=1))

        # distance to switch points
        if switch_points_arr.size:
            d_switch = np.sqrt(((candidates[:, None, :] - switch_points_arr[None, :, :]) ** 2).sum(axis=2))
            clearance = np.minimum(clearance, d_switch.min(axis=1))

        # distance to lines
        if line_segments:
            for A, B, AB, denom in line_segments:
                AP = candidates - A  # (12,2)
                t = (AP @ AB) / denom
                t = np.clip(t, 0.0, 1.0)
                proj = A + t[:, None] * AB
                d_line = np.sqrt(((candidates - proj) ** 2).sum(axis=1))
                clearance = np.minimum(clearance, d_line)

        # distance to already used text boxes
        if used_boxes:
            used_arr = np.asarray(used_boxes, dtype=float)
            d_used = np.sqrt(((candidates[:, None, :] - used_arr[None, :, :]) ** 2).sum(axis=2))
            clearance = np.minimum(clearance, d_used.min(axis=1))

        best_idx = int(np.argmax(clearance))
        best_pos = candidates[best_idx]
        used_boxes.append((best_pos[0], best_pos[1]))

        ax.text(
            best_pos[0],
            best_pos[1],
            text,
            fontsize=fontsize,
            color="#333333",
            ha="center",
            va="center",
        )

    # -------------------------------------------------
    # PRECOMPUTE BUS DATA
    # -------------------------------------------------
    bus_positive_P = {
        b: max(data["P"], 0.0)
        for b, data in buses.items()
    }

    energized_positive_sum = sum(bus_positive_P.get(b, 0.0) for b in energized_buses) * Sbase
    total_unserved = sum(
        bus_positive_P.get(b, 0.0)
        for b in buses
        if b not in energized_buses
    ) * Sbase

    # -------------------------------------------------
    # LINES
    # -------------------------------------------------
    for geom in valid_sections:
        x1, y1 = geom["p1"]
        x2, y2 = geom["p2"]
        ax.plot([x1, x2], [y1, y2], color=LINE_COLOR, linewidth=1.5, zorder=1)

    # -------------------------------------------------
    # POWER FLOW ARROWS
    # -------------------------------------------------
    if Pflows and parent:
        for child, par in parent.items():
            if child not in pos or par not in pos:
                continue

            x1, y1 = pos[par]
            x2, y2 = pos[child]

            dx, dy = x2 - x1, y2 - y1
            L = np.hypot(dx, dy)
            if L == 0:
                continue

            vx, vy = dx / L, dy / L
            mx, my = (x1 + x2) / 2, (y1 + y2) / 2

            p = Pflows.get(child, 0)
            if abs(p) < 1e-5:
                continue

            if p < 0:
                vx, vy = -vx, -vy

            ax.arrow(
                mx - 0.3 * vx, my - 0.3 * vy,
                0.6 * vx, 0.6 * vy,
                head_width=0.18, head_length=0.25,
                fc="#555555", ec="#555555",
                alpha=0.7, zorder=2
            )

            angle = np.degrees(np.arctan2(dy, dx))
            if angle > 90 or angle < -90:
                angle += 180

            offset = 0.25
            tx = mx - offset * vy
            ty = my + offset * vx

            ax.text(
                tx,
                ty,
                f"{abs(p * Sbase):.2f} MW",
                fontsize=5,
                ha="center",
                va="center",
                rotation=angle,
                rotation_mode="anchor",
                color="#444444",
                bbox=dict(
                    facecolor="white",
                    edgecolor="none",
                    alpha=0.7,
                    pad=0.2,
                ),
                zorder=3,
            )

    # -------------------------------------------------
    # SWITCHES + BREAKERS + FAULTS
    # -------------------------------------------------
    def draw_switch(p, open_flag):
        ax.scatter(
            p[0], p[1],
            s=25,
            marker="s",
            facecolor=SWITCH_OPEN if open_flag else SWITCH_CLOSED,
            edgecolor="black",
            linewidth=1.5,
            zorder=5,
        )

    def draw_cb(p, open_flag):
        ax.scatter(
            p[0], p[1],
            marker="x",
            s=80,
            linewidth=2,
            color="#d62728" if open_flag else "black",
            zorder=6,
        )

    for geom in valid_sections:
        s = geom["section"]
        p1 = geom["p1"]
        p2 = geom["p2"]
        v = geom["v"]

        disc = s["disc"]
        if disc in ("U", "B"):
            draw_switch(p1 + 0.6 * v, s.get("open_up", False))
        if disc in ("D", "B"):
            draw_switch(p2 - 0.6 * v, s.get("open_down", False))

        br = s.get("breaker", "N")
        if br in ("U", "B"):
            draw_cb(p1 + 0.6 * v, s.get("open_up", False))
        if br in ("D", "B"):
            draw_cb(p2 - 0.6 * v, s.get("open_down", False))

        if s.get("fault"):
            mid = (p1 + p2) / 2
            ax.text(mid[0], mid[1], "⚡", fontsize=24, color=FAULT_COLOR)

    # -------------------------------------------------
    # ROOT LOAD TEXT
    # -------------------------------------------------
    if switching_owner:
        for r in roots:
            if r not in pos:
                continue

            supplied_load = 0.0
            for b in energized_buses:
                if switching_owner.get(b) != r:
                    continue

                P = bus_positive_P.get(b, 0.0)
                Pbess = bess_power.get(b, 0.0)
                supplied_load += (P - Pbess)

            x, y = pos[r]
            ax.text(
                x,
                y + 1.2,
                f"{supplied_load * Sbase:.2f} MW",
                fontsize=9,
                weight="bold",
                color="navy",
                ha="center",
                bbox=dict(
                    facecolor="white",
                    edgecolor="lightgray",
                    boxstyle="round,pad=0.3",
                ),
                zorder=7,
            )

    # -------------------------------------------------
    # BUSES
    # -------------------------------------------------
    bess_nodes = set(bess_power.keys())

    for n, (x, y) in pos.items():
        has_bess = n in bess_nodes
        has_dg = has_bess

        if n in roots:
            face = ROOT_COLOR
        elif has_dg:
            face = DG_COLOR
        elif n in shed_nodes:
            face = SHED_COLOR
        elif n in energized_buses:
            face = ENERGIZED_COLOR
        else:
            face = ISO_COLOR

        marker = "s" if (n in roots or has_dg) else "o"

        ax.scatter(
            x, y,
            s=140,
            marker=marker,
            facecolor=face,
            edgecolor=BUS_EDGE,
            zorder=3,
        )

        ax.text(x, y, f"{n+1}", fontsize=6, ha="center", va="center")

        P = buses[n]["P"] * Sbase
        txt = ""

        if n in energized_buses:
            txt += f"{voltages.get(n, 0):.3f} pu\n"

        if P > 0:
            txt += f"{P:.2f} MW"

        if txt:
            place_text_smart(
                ax,
                x,
                y,
                txt,
                used_boxes,
                fontsize=5,
            )

        if n in bess_power:
            Pb = bess_power[n]
            if n not in energized_buses:
                Pb = 0.0

            ax.text(
                x,
                y - 0.9,
                f"BESS {Pb * Sbase:.2f} MW",
                fontsize=6,
                ha="center",
                color="purple",
            )

    # -------------------------------------------------
    # SUMMARY (FIXED POSITION)
    # -------------------------------------------------
    summary_text = (
        "System Summary\n"
        + "──────────────\n"
        + f"Served load   : {energized_positive_sum:.2f} MW\n"
        + f"Unserved load : {total_unserved:.2f} MW"
    )

    ax.text(
        0.02, 0.02,
        summary_text,
        transform=ax.transAxes,
        fontsize=10,
        family="monospace",
        verticalalignment="bottom",
        bbox=dict(
            facecolor="#f8f9fa",
            edgecolor="#444",
            boxstyle="round,pad=0.5",
        ),
    )

    # -------------------------------------------------
    # LEGEND
    # -------------------------------------------------
    legend_elements = [
        Line2D([0], [0], marker="s", color="w", markerfacecolor=ROOT_COLOR, label="Root"),
        Line2D([0], [0], marker="o", color="w", markerfacecolor=ENERGIZED_COLOR, label="Energized"),
        Line2D([0], [0], marker="o", color="w", markerfacecolor=SHED_COLOR, label="Shed"),
        Line2D([0], [0], marker="o", color="w", markerfacecolor=ISO_COLOR, label="Isolated"),
        Line2D([0], [0], marker="s", color="w", markerfacecolor=DG_COLOR, label="BESS"),
    ]

    ax.legend(handles=legend_elements, loc="upper left")

    ax.axis("off")
    ax.set_title("Distribution Network")

    plt.tight_layout()

    if show:
        plt.show()

    return fig

def plot_ens_lp(ENS_lp, network):

    import numpy as np
    import matplotlib.pyplot as plt

    load_buses = [
        b for b in network["buses"]
        if network["buses"][b]["P"] > 1e-9
    ]

    load_buses = sorted(load_buses)

    A = np.array([ENS_lp.get(b,0) for b in load_buses])

    order = np.argsort(A)[::-1]
    load_buses = [load_buses[i] for i in order]
    A = A[order]

    x = np.arange(len(load_buses))

    fig, ax1 = plt.subplots(figsize=(16,6))
    ax2 = ax1.twinx()

    ax1.bar(
        x,
        A,
        0.8,
        color="steelblue",
        label="ENS per LP"
    )

    ax2.plot(
        x,
        np.cumsum(A),
        linewidth=2,
        color="darkred",
        label="Cumulative ENS"
    )

    ax1.set_xticks(x)
    ax1.set_xticklabels([f"LP{b+1}" for b in load_buses], rotation=90)

    ax1.set_ylabel("ENS [MWh/year]")
    ax2.set_ylabel("Cumulative ENS [MWh/year]")

    ax1.set_title("ENS per Load Point")

    ax1.grid(alpha=0.3)

    h1,l1 = ax1.get_legend_handles_labels()
    h2,l2 = ax2.get_legend_handles_labels()

    ax1.legend(h1+h2,l1+l2)

    plt.tight_layout()
    plt.show()

if __name__ == "__main__":

    #test_system = "NEW_CODE/new_systems/IEEE_123Bus.xlsx"
    #test_system = "NEW_CODE/new_systems/20BusTest.xlsx"
    

    test_system = {"path": "NEW_CODE/new_systems/CINELDI.xlsx", "roots": [1,62,88,36]}
    #test_system = {"path": "NEW_CODE/new_systems/BUS 2 Case D.xlsx", "roots": [1+22,6+22, 8+22, 12+22, 16+22]}

    network = build_network(test_system["path"], use_lambda_temp=False)
    Sbase = 10 # MVA

    #network = reset_and_apply_switches(network)

    Vmin = 0.90
    cap_limit = 10
    contingency_sid = 6

    bess_buses = {
    #105: {"E":0.06, "P":0.03},
    #123: {"E":0.06, "P":0.03},
    #25: {"E":0.06, "P":0.03},
    }

    ENS_lp, results = run_analytical_pipeline(
    network,
    roots=test_system["roots"],
    Vmin=Vmin,
    Sbase=Sbase,
    cap_limit=cap_limit,
    contingency_sid=contingency_sid,
    bess_buses=bess_buses,
    )

    res = results[contingency_sid]

    fig = plot_network(
        pos=network["positions"],
        sections=res["sections"],
        voltages=res["voltages"],
        energized_buses=res["energized_buses"],
        buses=network["buses"],
        switching_owner=res["switching_owner"],
        shed_nodes=res["shed_nodes"],
        roots=res["roots"],
        bess_power=res["bess_power"],
        Pflows=res["Pflows"],
        parent=res["parent"],
        Sbase=Sbase,
        show=True,
    )

    ens_lp_analytical = run_analytical(
        network,
        roots=test_system["roots"],
        Vmin=Vmin,
        Sbase=Sbase,
        cap_limit=cap_limit,
    )
    print("Total ENS (analytical):", sum(ens_lp_analytical.values()))

    plot_ens_lp(ens_lp_analytical, network)

