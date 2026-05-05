import matplotlib.pyplot as plt
import numpy as np
from matplotlib.lines import Line2D

def plot_network(
    pos,
    lines,
    voltages,
    energized_buses,
    buses,
    switching_owner=None,
    shed_nodes=None,
    slack_buses=None,
    BESS_buses=None,
    BESS_power=None,
    supply_type_mapping=None,
    Pflows=None,
    parent=None,
    Sbase=1,
    show=False,
):
    """
    Plots the power system network with detailed visualization of the system state after
    restoration from a contingency. 

    The plot shows the buses, lines, and switch states, together with annotations
    for load demand, bus voltages, BESS status, and slack bus generation.
    """
    
    BESS_buses = BESS_buses or {}
    BESS_power = BESS_power or {}
    supply_type_mapping = supply_type_mapping or {}
    shed_nodes = set(shed_nodes or [])
    slack_buses = set(slack_buses or [])
    energized_buses = set(energized_buses)
    switching_owner = switching_owner or {}

    fig, ax = plt.subplots(figsize=(15, 9))
    used_boxes = []

    LINE_COLOR, SWITCH_OPEN, SWITCH_CLOSED = "#2c2c2c", "#d62728", "#FEFAFA"
    SLACK_COLOR, ENERGIZED_COLOR, SHED_COLOR = "#1870d3", "#4ae27a", "#ff9f1c"
    ISO_COLOR, DG_COLOR, BUS_EDGE, FAULT_COLOR = "#878383", "#b07cff", "black", "red"

    valid_lines, line_segments, switch_points = [], [], []

    for s in lines.values():
        up, down = s["up"], s["down"]
        if up not in pos or down not in pos:
            continue
        p1, p2 = np.asarray(pos[up], float), np.asarray(pos[down], float)
        vec = p2 - p1
        L = np.linalg.norm(vec)
        if L == 0:
            continue
        v = vec / L
        AB = vec
        geom = {"line": s, "p1": p1, "p2": p2, "v": v, "A": p1, "B": p2, "AB": AB, "denom": float(np.dot(AB, AB))}
        valid_lines.append(geom)
        line_segments.append((p1, p2, AB, geom["denom"]))
        disc = s["disc"]
        if disc in ("U", "B"):
            switch_points.append(p1 + 0.6 * v)
        if disc in ("D", "B"):
            switch_points.append(p2 - 0.6 * v)

    node_points = np.array(list(pos.values()), float) if pos else np.empty((0, 2), float)
    switch_points_arr = np.array(switch_points, float) if switch_points else np.empty((0, 2), float)

    angles = np.linspace(0, 2 * np.pi, 12, endpoint=False)
    base_radius, vertical_shrink = 1.3, 0.25
    cos_a, sin_a = np.cos(angles), np.sin(angles)
    radii = base_radius - vertical_shrink * (sin_a ** 2)

    def place_text_smart(ax, x, y, text, used_boxes, fontsize=6):
        candidates = np.column_stack((x + radii * cos_a, y + radii * sin_a))
        clearance = np.full(len(candidates), np.inf, float)

        if node_points.size:
            clearance = np.minimum(clearance, np.sqrt(((candidates[:, None, :] - node_points[None, :, :]) ** 2).sum(2)).min(1))
        if switch_points_arr.size:
            clearance = np.minimum(clearance, np.sqrt(((candidates[:, None, :] - switch_points_arr[None, :, :]) ** 2).sum(2)).min(1))
        for A, B, AB, denom in line_segments:
            AP = candidates - A
            t = np.clip((AP @ AB) / denom, 0.0, 1.0)
            proj = A + t[:, None] * AB
            clearance = np.minimum(clearance, np.sqrt(((candidates - proj) ** 2).sum(1)))
        if used_boxes:
            used_arr = np.asarray(used_boxes, float)
            clearance = np.minimum(clearance, np.sqrt(((candidates[:, None, :] - used_arr[None, :, :]) ** 2).sum(2)).min(1))

        best_pos = candidates[int(np.argmax(clearance))]
        used_boxes.append((best_pos[0], best_pos[1]))
        ax.text(best_pos[0], best_pos[1], text, fontsize=fontsize, color="#333333", ha="center", va="center")

    bus_positive_P = {b: max(data["P"], 0.0) for b, data in buses.items()}
    
    for geom in valid_lines:
        x1, y1 = geom["p1"]
        x2, y2 = geom["p2"]
        ax.plot([x1, x2], [y1, y2], color=LINE_COLOR, linewidth=1.5, zorder=1)

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

            ax.arrow(mx - 0.3 * vx, my - 0.3 * vy, 0.6 * vx, 0.6 * vy, head_width=0.18, head_length=0.25, fc="#555555", ec="#555555", alpha=0.7, zorder=2)

            angle = np.degrees(np.arctan2(dy, dx))
            if angle > 90 or angle < -90:
                angle += 180

            offset = 0.45
            tx, ty = mx - offset * vy, my + offset * vx
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
                bbox=dict(facecolor="white", edgecolor="none", alpha=0.7, pad=0.2),
                zorder=3,
            )

    def draw_switch(p, open_flag):
        ax.scatter(p[0], p[1], s=25, marker="s", facecolor=SWITCH_OPEN if open_flag else SWITCH_CLOSED, edgecolor="black", linewidth=1.5, zorder=5)

    def draw_cb(p, open_flag):
        ax.scatter(p[0], p[1], marker="x", s=80, linewidth=2, color="#d62728" if open_flag else "black", zorder=6)

    for geom in valid_lines:
        s, p1, p2, v = geom["line"], geom["p1"], geom["p2"], geom["v"]
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

    all_supply_buses = set(switching_owner.values())
    bess_nodes = {ext_bus - 1 for ext_bus in BESS_buses.keys()}

    if switching_owner:
        for supply_bus in all_supply_buses:
            if supply_bus not in pos:
                continue

            supplied_load = sum(
                bus_positive_P.get(b, 0.0) - BESS_power.get(b, 0.0)
                for b in energized_buses
                if switching_owner.get(b) == supply_bus
            )

            x, y = pos[supply_bus]
            color = "navy" if supply_type_mapping.get(supply_bus) != "bess_slack" else "purple"

            ax.text(
                x,
                y + 1.2,
                f"{supplied_load * Sbase:.2f} MW",
                fontsize=9,
                weight="bold",
                color=color,
                ha="center",
                bbox=dict(facecolor="white", edgecolor="lightgray", boxstyle="round,pad=0.3"),
                zorder=7,
            )

    for n, (x, y) in pos.items():
        has_bess = n in bess_nodes
        supply_type = supply_type_mapping.get(n)

        is_grid_slack = n in slack_buses
        is_bess_slack = supply_type == "bess_slack" and n in all_supply_buses

        if is_grid_slack:
            face = SLACK_COLOR
            marker = "s"
        elif is_bess_slack:
            face = DG_COLOR
            marker = "s"
        elif n in shed_nodes:
            face = SHED_COLOR
            marker = "o"
        elif n in energized_buses:
            face = ENERGIZED_COLOR
            marker = "o"
        else:
            face = ISO_COLOR
            marker = "o"

        edgecolor = "purple" if has_bess and not is_bess_slack else BUS_EDGE
        linewidth = 2 if has_bess else 1

        ax.scatter(
            x,
            y,
            s=140,
            marker=marker,
            facecolor=face,
            edgecolor=edgecolor,
            linewidth=linewidth,
            zorder=3
        )
        ax.text(x, y, f"{n+1}", fontsize=6, ha="center", va="center")

        P = buses[n]["P"] * Sbase
        txt = (f"{voltages.get(n, 0):.4f} pu\n" if n in energized_buses else "") + (f"{P:.2f} MW" if P > 0 else "")
        if txt:
            place_text_smart(ax, x, y, txt, used_boxes, fontsize=5)

        if has_bess:
            if is_bess_slack:
                bess_label = "BESS slack"
            else:
                Pb = BESS_power.get(n, 0.0) if n in energized_buses else 0.0
                bess_label = f"BESS {Pb * Sbase:.2f} MW"
            ax.text(x, y - 0.7, bess_label, fontsize=6, ha="center", color="purple")


    legend_elements = [
        Line2D([0], [0], marker="s", color="w", markerfacecolor=SLACK_COLOR, label="Grid slack"),
        Line2D([0], [0], marker="s", color="w", markerfacecolor=DG_COLOR, label="BESS slack"),
        Line2D([0], [0], marker="o", color="w", markerfacecolor=ENERGIZED_COLOR, label="Energized"),
        Line2D([0], [0], marker="o", color="w", markerfacecolor=SHED_COLOR, label="Shed"),
        Line2D([0], [0], marker="o", color="w", markerfacecolor=ISO_COLOR, label="Isolated"),
        Line2D([0], [0], marker="o", color="w", markerfacecolor="white", markeredgecolor="purple", label="BESS location"),
        Line2D([0], [0], marker="s", color="w", markerfacecolor=SWITCH_CLOSED,
               markeredgecolor="black", label="Closed disconnector"),
        Line2D([0], [0], marker="s", color="w", markerfacecolor=SWITCH_OPEN,
               markeredgecolor="black", label="Open disconnector"),
        Line2D([0], [0], marker="x", color="black", linestyle="None",
               markersize=8, markeredgewidth=2, label="Closed CB"),
        Line2D([0], [0], marker="x", color="#d62728", linestyle="None",
               markersize=8, markeredgewidth=2, label="Open CB"),
        Line2D([0], [0], marker=r"$⚡$", color=FAULT_COLOR, linestyle="None",
               markersize=14, label="Fault"),
    ]

    ax.legend(handles=legend_elements, loc="upper left")
    ax.axis("off")
    plt.tight_layout()

    if show:
        plt.show()
