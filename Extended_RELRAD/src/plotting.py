import matplotlib.pyplot as plt
import numpy as np
from matplotlib.lines import Line2D
from collections import OrderedDict
import re
from matplotlib.ticker import MaxNLocator
from matplotlib.legend_handler import HandlerBase
from matplotlib.patches import Rectangle

'''
Copyright (C) 2026 Jørgen Bratvold.

Part of a GPLv3-licensed thesis implementation derived in part from
RELRAD-software by Sondre Modalsli Aaberg.

Licensed under the GNU General Public License v3.0 or later.
See LICENSE for details.
'''

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

def plot_case_study_results(
    details,
    network,
    all_cases,
    sort_by=None,
    figsize=(16, 12),
    top_n=None,
    same_load_point_order=True,
):
    """
    Plot the results of a case study with multiple scenarios.

    args:
        details: Dictionary with detailed results for each scenario, as returned by run_case_study.
        network: The network data structure used in the case study, needed for load point information.
        all_cases: List of case definitions, as provided to run_case_study.
        sort_by: Scenario name used to rank load points in the plot. If None, the first scenario in scenarios is used.
        same_load_point_order: If True, all scenarios will be plotted with load points in the same order, determined by the sort_by scenario. If False, each scenario will be plotted with load points sorted by their own ENS values.
        figsize: Size of the figure to create.
        top_n: If specified, only plot the top N load points by ENS in the sort_by scenario.
        same_load_point_order: If True, all scenarios will be plotted with load points in the same order, determined by the sort_by scenario. If False, each scenario will be plotted with load points sorted by their own ENS values.

    returns:
        fig: The matplotlib figure object containing the plot.
    """

    class HandlerBarLine(HandlerBase):
        """
        Custom legend handler to show both a bar and a line in the same legend entry.
        """

        def create_artists(
        self,
        _legend,
        orig_handle,
        xdescent,
        ydescent,
        width,
        height,
        _fontsize,
        trans,
    ):
            bar_handle, line_handle = orig_handle

            x0 = xdescent + 0.08 * width
            w = 0.84 * width

            bar_h = 0.26 * height
            bar_y = ydescent + 0.35 * height
            line_y = ydescent - 0.35 * height

            bar = Rectangle(
                (x0, bar_y),
                w,
                bar_h,
                facecolor=bar_handle.get_facecolor(),
                edgecolor=bar_handle.get_edgecolor(),
                hatch=bar_handle.get_hatch(),
                linewidth=bar_handle.get_linewidth(),
                alpha=bar_handle.get_alpha(),
                transform=trans,
            )

            line = Line2D(
                [x0, x0 + w],
                [line_y, line_y],
                color=line_handle.get_color(),
                linestyle=line_handle.get_linestyle(),
                linewidth=line_handle.get_linewidth(),
                solid_capstyle="round",
                transform=trans,
            )

            return [bar, line]
        
    def strip_bess_suffix(name):
        return re.sub(r"-BESS(?:\d+)?(?:-(?:grid|island))?$", "", name)

    def has_bess(name):
        return "-BESS" in name

    def scenario_variant(name):
        if not has_bess(name):
            return "no_bess"
        if name.endswith("-BESS-grid"):
            return "bess_grid"
        if name.endswith("-BESS-island"):
            return "bess_island"
        return "bess_only"

    def compute_symmetric_label_positions(endpoints, min_sep):
        adjusted = [y for _, y, _ in endpoints]

        if not adjusted:
            return adjusted

        center = 0.5 * (len(adjusted) - 1)

        for i in range(len(adjusted)):
            adjusted[i] += (i - center) * min_sep

        for i in range(1, len(adjusted)):
            if adjusted[i] < adjusted[i - 1] + 0.65 * min_sep:
                adjusted[i] = adjusted[i - 1] + 0.65 * min_sep

        return adjusted

    def annotate_endpoints(
        ax_cum,
        endpoints,
        x_last,
        text_color,
        x_text_offset=1.15,
        min_sep_factor=0.1,
        right_padding=3.8,
        linestyle_getter=None,
        reference_value=None,
    ):
        if not endpoints:
            ax_cum.set_xlim(-0.5, 1.0)
            return

        endpoints = sorted(endpoints, key=lambda t: t[1])
        yvals = [v for _, v, _ in endpoints]
        ymax = max(yvals) if yvals else 1.0

        min_sep = min(2.6, min_sep_factor * ymax) if ymax > 0 else 0.25
        adjusted = compute_symmetric_label_positions(endpoints, min_sep)

        x_text = x_last + x_text_offset

        for sc, y_end, style_value in endpoints:
            pass

        for (sc, y_end, style_value), y_text in zip(endpoints, adjusted):
            color, linestyle = linestyle_getter(sc, style_value)

            ax_cum.scatter(
                x_last,
                y_end,
                color=color,
                s=34,
                zorder=5,
                edgecolor="black",
                linewidth=0.4,
            )

            if reference_value is not None and reference_value != 0:
                pct_change = 100 * (y_end - reference_value) / reference_value
                label = f"{y_end:.2f} ({pct_change:+.1f}%)"
            else:
                label = f"{y_end:.2f}"

            ax_cum.annotate(
                label,
                xy=(x_last, y_end),
                xytext=(x_text, y_text),
                textcoords="data",
                va="center",
                ha="left",
                fontsize=12,
                color=text_color,
                arrowprops=dict(
                    arrowstyle="-",
                    color=color,
                    lw=1.2,
                    alpha=0.95,
                    linestyle=linestyle,
                    shrinkA=0,
                    shrinkB=0,
                    relpos=(0.0, 0.5),
                ),
            )

        ax_cum.set_xlim(-0.5, x_last + right_padding)

    def style_legend(leg, fontsize=12):
        frame = leg.get_frame()
        frame.set_linewidth(1.2)
        frame.set_edgecolor("black")
        frame.set_facecolor("white")
        frame.set_alpha(1.0)

        for txt in leg.get_texts():
            txt.set_color("black")
            txt.set_fontsize(fontsize)

    scenario_names = list(details.keys())
    if not scenario_names:
        raise ValueError("details er tom.")

    load_buses = sorted(
        b for b in network["buses"]
        if network["buses"][b]["P"] > 1e-9
    )
    if not load_buses:
        raise ValueError("Fant ingen load buses i network.")

    scenario_slack_buses = {
        sc["name"]: tuple(sc["slack_buses"])
        for sc in all_cases
    }

    missing = [sc for sc in scenario_names if sc not in scenario_slack_buses]
    if missing:
        raise KeyError(
            f"Disse scenarioene finnes i details, men ikke i scenarios: {missing}"
        )

    text_color = "black"
    grid_color = "#D9D9D9"
    spine_color = "black"

    plt.rcParams.update({
        "figure.facecolor": "white",
        "axes.facecolor": "white",
        "savefig.facecolor": "white",

        "font.size": 12,
        "axes.titlesize": 12,
        "axes.labelsize": 12,
        "xtick.labelsize": 12,
        "ytick.labelsize": 12,
        "legend.fontsize": 12,

        "axes.edgecolor": "black",
        "axes.linewidth": 1.0,
        "xtick.color": "black",
        "ytick.color": "black",
        "axes.labelcolor": "black",
        "text.color": "black",

        "legend.frameon": True,
        "legend.facecolor": "white",
        "legend.edgecolor": "black",
        "legend.framealpha": 1.0,
        "legend.fancybox": False,

        "hatch.linewidth": 0.8,
        "pdf.fonttype": 42,
        "ps.fonttype": 42,
    })

    rc_groups = OrderedDict()
    for sc in scenario_names:
        rc_key = scenario_slack_buses[sc]
        rc_groups.setdefault(rc_key, []).append(sc)

    grouped = OrderedDict()

    for rc_key, rc_scenarios in rc_groups.items():
        rc_has_bess = any(has_bess(sc) for sc in rc_scenarios)

        if not rc_has_bess:
            grouped[(rc_key, "all_cases")] = list(rc_scenarios)
            continue

        tmp = OrderedDict()
        for sc in rc_scenarios:
            base_name = strip_bess_suffix(sc)
            tmp.setdefault(base_name, []).append(sc)

        variant_order = {
            "no_bess": 0,
            "bess_only": 1,
            "bess_grid": 1,
            "bess_island": 2,
        }

        for base_name, sc_list in tmp.items():
            grouped[(rc_key, base_name)] = sorted(
                sc_list,
                key=lambda sc_name: variant_order[scenario_variant(sc_name)],
            )

    n_groups = len(grouped)

    bess_colors = [
        "#4C78A8",
        "#F58518",
        "#54A24B",
        "#E45756",
        "#72B7B2",
        "#B279A2",
        "#9D755D",
        "#BAB0AC",
        "#FF9DA6",
        "#8CD17D",
        "#79706E",
        "#D4A6C8",
    ]

    no_bess_group_colors = [
    "#4C78A8", 
    "#F58518",
    "#54A24B", 
    "#E45756", 
    "#B279A2", 
]

    color_map_bess = {}
    color_map_no_bess = {}

    bess_group_keys = [
        group_key for group_key in grouped
        if group_key[1] != "all_cases"
    ]

    for i, group_key in enumerate(bess_group_keys):
        color_map_bess[group_key] = bess_colors[i % len(bess_colors)]

    for group_key, sc_list in grouped.items():
        if group_key[1] == "all_cases":
            for i, sc in enumerate(sc_list):
                color_map_no_bess[sc] = no_bess_group_colors[
                    i % len(no_bess_group_colors)
                ]

    fig, axes = plt.subplots(
        n_groups,
        1,
        figsize=figsize,
        squeeze=False,
        sharex=False,
    )
    axes = axes.flatten()

    global_order = None

    for row, ((rc_key, subgroup_name), scenario_group) in enumerate(grouped.items()):
        ax = axes[row]
        ax_cum = ax.twinx()

        if sort_by in scenario_group:
            ref_case = sort_by
        elif subgroup_name != "all_cases" and subgroup_name in scenario_group:
            ref_case = subgroup_name
        else:
            ref_case = scenario_group[0]

        ens_matrix = {
            sc: np.array(
                [details[sc]["ENS_per_bus"].get(b, 0.0) for b in load_buses],
                dtype=float,
            )
            for sc in scenario_group
        }

        if same_load_point_order:
            if global_order is None:
                global_order = np.argsort(ens_matrix[ref_case])[::-1]

                if top_n is not None:
                    global_order = global_order[:top_n]

            order = global_order

        else:
            order = np.argsort(ens_matrix[ref_case])[::-1]

            if top_n is not None:
                order = order[:top_n]

        load_buses_sorted = [load_buses[i] for i in order]
        ens_matrix = {
            sc: vals[order]
            for sc, vals in ens_matrix.items()
        }

        x = np.arange(len(load_buses_sorted))
        is_bess_subplot = subgroup_name != "all_cases"

        if is_bess_subplot:
            n_sc = len(scenario_group)
            width = min(0.8 / max(n_sc, 1), 0.22)
            base_color = color_map_bess[(rc_key, subgroup_name)]

            variant_styles = {
                "no_bess": {
                    "alpha": 0.35,
                    "hatch": None,
                    "edgecolor": base_color,
                    "linewidth": 0.8,
                    "linestyle": "--",
                },
                "bess_only": {
                    "alpha": 0.65,
                    "hatch": "///",
                    "edgecolor": base_color,
                    "linewidth": 0.8,
                    "linestyle": "-",
                },
                "bess_grid": {
                    "alpha": 0.65,
                    "hatch": "///",
                    "edgecolor": base_color,
                    "linewidth": 0.8,
                    "linestyle": "-.",
                },
                "bess_island": {
                    "alpha": 1.00,
                    "hatch": "///",
                    "edgecolor": base_color,
                    "linewidth": 0.8,
                    "linestyle": "-",
                },
            }

            endpoints = []
            legend_items = []

            for i, sc in enumerate(scenario_group):
                variant = scenario_variant(sc)
                style = variant_styles[variant]
                offset = (i - (n_sc - 1) / 2) * width

                ax.bar(
                    x + offset,
                    ens_matrix[sc],
                    width=width * 0.70,
                    color=base_color,
                    alpha=style["alpha"],
                    hatch=style["hatch"],
                    edgecolor=style["edgecolor"],
                    linewidth=style["linewidth"],
                    zorder=2,
                )

                y = np.cumsum(ens_matrix[sc])

                ax_cum.plot(
                    x,
                    y,
                    color=base_color,
                    linestyle=style["linestyle"],
                    linewidth=2.8,
                    solid_capstyle="round",
                    zorder=3,
                )

                if len(x) > 0:
                    endpoints.append((sc, y[-1], variant))

                bar_handle = Rectangle(
                    (0, 0),
                    1,
                    1,
                    facecolor=base_color,
                    alpha=style["alpha"],
                    edgecolor=style["edgecolor"],
                    hatch=style["hatch"],
                    linewidth=0.9,
                )

                line_handle = Line2D(
                    [0],
                    [0],
                    color=base_color,
                    linestyle=style["linestyle"],
                    lw=2.8,
                )

                legend_items.append((sc, (bar_handle, line_handle)))

            if len(x) > 0:
                reference_value = None
                for sc_ref, y_ref, _ in endpoints:
                    if sc_ref == ref_case:
                        reference_value = y_ref
                        break

                annotate_endpoints(
                    ax_cum=ax_cum,
                    endpoints=endpoints,
                    x_last=x[-1],
                    text_color=text_color,
                    x_text_offset=1.15,
                    min_sep_factor=0.1,
                    right_padding=max(4.0, 0.14 * len(x)),
                    linestyle_getter=lambda sc, variant: (
                        base_color,
                        variant_styles[variant]["linestyle"],
                    ),
                    reference_value=reference_value,
                )

            ax.set_xlim(ax_cum.get_xlim())

            dedup = OrderedDict()
            for label, handle_pair in legend_items:
                dedup[label] = handle_pair

            legend_labels = list(dedup.keys())
            legend_handles = list(dedup.values())

            leg = ax.legend(
                handles=legend_handles,
                labels=legend_labels,
                handler_map={tuple: HandlerBarLine()},
                loc="upper left",
                bbox_to_anchor=(0.0, 1.2),
                ncols=min(len(legend_handles), 4),
                borderaxespad=0.0,
                handlelength=3.2,
                handleheight=1.4,
                columnspacing=1.5,
                handletextpad=0.8,
                labelspacing=0.7,
                fontsize=12,
                frameon=True,
                facecolor="white",
                edgecolor="black",
                framealpha=1.0,
                fancybox=False,
            )
            style_legend(leg, fontsize=12)

        else:
            n_sc = len(scenario_group)
            width = min(0.8 / max(n_sc, 1), 0.22)

            endpoints = []

            for i, sc in enumerate(scenario_group):
                color = color_map_no_bess[sc]
                offset = (i - (n_sc - 1) / 2) * width

                ax.bar(
                    x + offset,
                    ens_matrix[sc],
                    width=width * 0.70,
                    color=color,
                    alpha=0.90,
                    edgecolor="black",
                    linewidth=0.45,
                    zorder=2,)

                y = np.cumsum(ens_matrix[sc])

                ax_cum.plot(
                    x,
                    y,
                    color=color,
                    linestyle="-",
                    linewidth=3.0,
                    solid_capstyle="round",
                    zorder=3,
                )

                if len(x) > 0:
                    endpoints.append((sc, y[-1], color))

            if len(x) > 0:
                reference_value = None
                for sc_ref, y_ref, _ in endpoints:
                    if sc_ref == ref_case:
                        reference_value = y_ref
                        break

                annotate_endpoints(
                    ax_cum=ax_cum,
                    endpoints=endpoints,
                    x_last=x[-1],
                    text_color=text_color,
                    x_text_offset=1.15,
                    min_sep_factor=0.1,
                    right_padding=max(4.0, 0.14 * len(x)),
                    linestyle_getter=lambda sc, color: (
                        color,
                        "-",
                    ),
                    reference_value=reference_value,
                )

            ax.set_xlim(ax_cum.get_xlim())

            handles = [
                Line2D(
                    [0],
                    [0],
                    color=color_map_no_bess[sc],
                    linestyle="-",
                    lw=3.2,
                    label=sc,
                )
                for sc in scenario_group
            ]

            leg = ax.legend(
                handles=handles,
                loc="upper left",
                bbox_to_anchor=(0.0, 1.2),
                ncols=len(handles),
                borderaxespad=0.0,
                handlelength=3.2,
                handleheight=1.5,
                columnspacing=1.5,
                handletextpad=0.8,
                labelspacing=0.7,
                fontsize=12,
                frameon=True,
                facecolor="white",
                edgecolor="black",
                framealpha=1.0,
                fancybox=False,
            )
            style_legend(leg, fontsize=12)

        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)
        ax.spines["left"].set_color(spine_color)
        ax.spines["bottom"].set_color(spine_color)
        ax.spines["left"].set_linewidth(1.0)
        ax.spines["bottom"].set_linewidth(1.0)

        ax_cum.spines["top"].set_visible(False)
        ax_cum.spines["left"].set_visible(False)
        ax_cum.spines["right"].set_color(spine_color)
        ax_cum.spines["bottom"].set_visible(False)
        ax_cum.spines["right"].set_linewidth(1.0)

        ax.grid(axis="y", color=grid_color, linewidth=1.0)
        ax.set_axisbelow(True)

        ax.set_ylabel(
            "ENS per LP [MWh/year]",
            fontsize=12,
            color=text_color,
            labelpad=8,
        )

        ax_cum.set_ylabel(
            "Aggregated ENS [MWh/year]",
            fontsize=12,
            color=text_color,
            labelpad=8,
        )

        ax.set_xticks(x)
        ax.set_xticklabels(
            [f"{b + 1}" for b in load_buses_sorted],
            rotation=90,
            color=text_color,
            fontsize=12,
        )

        ax.set_xlabel(
            "Load points",
            fontsize=12,
            color=text_color,
            labelpad=4,
        )

        ax.tick_params(
            axis="x",
            colors=text_color,
            labelsize=12,
            width=1.0,
        )

        ax.tick_params(
            axis="y",
            colors=text_color,
            labelsize=12,
            width=1.0,
        )

        ax_cum.tick_params(
            axis="y",
            colors=text_color,
            labelsize=12,
            width=1.0,
        )

        ax.yaxis.set_major_locator(MaxNLocator(nbins=8))
        ax_cum.yaxis.set_major_locator(MaxNLocator(nbins=8))

    plt.tight_layout(rect=[0.005, 0.005, 0.995, 0.995])

    plt.show()

    return fig

def plot_RBTS_case_studies(
    details,
    networks_by_scenario,
    sort_by="Base-A",
    same_load_point_order=True,
    figsize=(16, 8),
    top_n=None,
):
    """
    Plot the base cases A to F from the provided details.
    """
    
    scenario_names = list(details.keys())

    if not scenario_names:
        raise ValueError("details er tom.")

    if sort_by not in scenario_names:
        sort_by = scenario_names[0]

    text_color = "black"
    grid_color = "#D9D9D9"
    spine_color = "black"

    plt.rcParams.update({
        "figure.facecolor": "white",
        "axes.facecolor": "white",
        "savefig.facecolor": "white",

        "font.size": 12,
        "axes.titlesize": 13,
        "axes.labelsize": 12,
        "xtick.labelsize": 11,
        "ytick.labelsize": 12,
        "legend.fontsize": 12,

        "axes.edgecolor": "black",
        "axes.linewidth": 1.0,
        "xtick.color": "black",
        "ytick.color": "black",
        "axes.labelcolor": "black",
        "text.color": "black",

        "legend.frameon": True,
        "legend.facecolor": "white",
        "legend.edgecolor": "black",
        "legend.framealpha": 1.0,
        "legend.fancybox": False,

        "pdf.fonttype": 42,
        "ps.fonttype": 42,
    })

    colors = [
        "#4C78A8",
        "#F58518",
        "#54A24B",
        "#E45756",
        "#B279A2",
        "#72B7B2",
    ]

    color_map = {
        sc: colors[i % len(colors)]
        for i, sc in enumerate(scenario_names)
    }

    ref_network = networks_by_scenario[sort_by]

    ref_load_buses = sorted(
        b for b in ref_network["buses"]
        if ref_network["buses"][b]["P"] > 1e-9
    )

    if not ref_load_buses:
        raise ValueError(f"Fant ingen load buses i {sort_by}.")

    ref_ens = np.array(
        [details[sort_by]["ENS_per_bus"].get(b, 0.0) for b in ref_load_buses],
        dtype=float,
    )

    ref_order = np.argsort(ref_ens)[::-1]

    if top_n is not None:
        ref_order = ref_order[:top_n]

    ref_load_buses_sorted = [ref_load_buses[i] for i in ref_order]

    fig, ax = plt.subplots(
        1,
        1,
        figsize=figsize,
    )

    ax_cum = ax.twinx()

    x = np.arange(len(ref_load_buses_sorted))
    n_sc = len(scenario_names)
    width = min(0.82 / max(n_sc, 1), 0.14)

    endpoints = []

    for i, sc in enumerate(scenario_names):
        network = networks_by_scenario[sc]

        load_buses_this = sorted(
            b for b in network["buses"]
            if network["buses"][b]["P"] > 1e-9
        )

        if same_load_point_order:
            buses_to_plot = ref_load_buses_sorted
        else:
            ens_this_all = np.array(
                [details[sc]["ENS_per_bus"].get(b, 0.0) for b in load_buses_this],
                dtype=float,
            )

            order_this = np.argsort(ens_this_all)[::-1]

            if top_n is not None:
                order_this = order_this[:top_n]

            buses_to_plot = [load_buses_this[j] for j in order_this]

        ens_values = np.array(
            [details[sc]["ENS_per_bus"].get(b, 0.0) for b in buses_to_plot],
            dtype=float,
        )

        if len(ens_values) != len(x):
            raise ValueError(
                f"{sc} har {len(ens_values)} load points, men referansen "
                f"{sort_by} har {len(x)}. Bruk separate subplots eller sjekk at "
                "A-F har samme load point-sett."
            )

        color = color_map[sc]
        offset = (i - (n_sc - 1) / 2) * width

        ax.bar(
            x + offset,
            ens_values,
            width=width * 0.82,
            color=color,
            alpha=0.82,
            edgecolor="black",
            linewidth=0.45,
            zorder=2,
        )

        y_cum = np.cumsum(ens_values)

        ax_cum.plot(
            x,
            y_cum,
            color=color,
            linestyle="-",
            linewidth=2.8,
            solid_capstyle="round",
            zorder=3,
        )

        if len(x) > 0:
            endpoints.append((sc, y_cum[-1], color))

    if endpoints:
        endpoints_sorted = sorted(endpoints, key=lambda t: t[1])
        ymax = max(y for _, y, _ in endpoints_sorted)
        min_sep = min(2.6, 0.08 * ymax) if ymax > 0 else 0.25

        adjusted_y = [y for _, y, _ in endpoints_sorted]

        for j in range(1, len(adjusted_y)):
            if adjusted_y[j] < adjusted_y[j - 1] + min_sep:
                adjusted_y[j] = adjusted_y[j - 1] + min_sep

        x_last = x[-1]
        x_text = x_last + max(1.2, 0.03 * len(x))
        reference_value = details[sort_by]["total_ENS"]

        for (sc, y_end, color), y_text in zip(endpoints_sorted, adjusted_y):
            ax_cum.scatter(
                x_last,
                y_end,
                color=color,
                s=36,
                zorder=5,
                edgecolor="black",
                linewidth=0.4,
            )

            if reference_value != 0:
                pct_change = 100 * (y_end - reference_value) / reference_value
                label = f"{sc}: {y_end:.2f} ({pct_change:+.1f}%)"
            else:
                label = f"{sc}: {y_end:.2f}"

            ax_cum.annotate(
                label,
                xy=(x_last, y_end),
                xytext=(x_text, y_text),
                textcoords="data",
                va="center",
                ha="left",
                fontsize=11,
                color=text_color,
                arrowprops=dict(
                    arrowstyle="-",
                    color=color,
                    lw=1.2,
                    alpha=0.95,
                    shrinkA=0,
                    shrinkB=0,
                    relpos=(0.0, 0.5),
                ),
            )

        ax.set_xlim(-0.5, x_last + max(6.0, 0.23 * len(x)))

    ax.set_ylabel(
        "ENS per LP [MWh/year]",
        fontsize=12,
        color=text_color,
        labelpad=8,
    )

    ax_cum.set_ylabel(
        "Aggregated ENS [MWh/year]",
        fontsize=12,
        color=text_color,
        labelpad=8,
    )

    ax.set_xlabel(
        "Load points",
        fontsize=12,
        color=text_color,
        labelpad=4,
    )

    ax.set_xticks(x)
    ax.set_xticklabels(
        [f"{b + 1}" for b in ref_load_buses_sorted],
        rotation=90,
        color=text_color,
        fontsize=11,
    )

    ax.grid(axis="y", color=grid_color, linewidth=1.0)
    ax.set_axisbelow(True)

    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.spines["left"].set_color(spine_color)
    ax.spines["bottom"].set_color(spine_color)

    ax_cum.spines["top"].set_visible(False)
    ax_cum.spines["left"].set_visible(False)
    ax_cum.spines["right"].set_color(spine_color)
    ax_cum.spines["bottom"].set_visible(False)

    ax.yaxis.set_major_locator(MaxNLocator(nbins=8))
    ax_cum.yaxis.set_major_locator(MaxNLocator(nbins=8))

    handles = [
        Line2D(
            [0],
            [0],
            color=color_map[sc],
            linestyle="-",
            lw=3.0,
            label=sc,
        )
        for sc in scenario_names
    ]

    leg = ax.legend(
        handles=handles,
        loc="upper left",
        bbox_to_anchor=(0.0, 1.12),
        ncols=min(len(handles), 6),
        borderaxespad=0.0,
        handlelength=3.0,
        columnspacing=1.4,
        handletextpad=0.7,
        fontsize=12,
        frameon=True,
        facecolor="white",
        edgecolor="black",
        framealpha=1.0,
        fancybox=False,
    )

    frame = leg.get_frame()
    frame.set_linewidth(1.1)
    frame.set_edgecolor("black")
    frame.set_facecolor("white")
    frame.set_alpha(1.0)

    plt.tight_layout(rect=[0.005, 0.005, 0.995, 0.96])
    plt.show()

    return fig
