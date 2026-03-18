import matplotlib.pyplot as plt
import matplotlib.patches as patches
from matplotlib.patches import Polygon
import networkx as nx
import pandas as pd
import numpy as np
import matplotlib.cm as cm
import matplotlib.colors as mcolors
from matplotlib.lines import Line2D
from matplotlib.legend_handler import HandlerTuple

def draw_node_labels(
        ax,
        pos,
        labels,
        nodelist,
        node_colors,
        fontsize=7):
    """
    Draw node labels with automatic contrast color.
    """

    def luminance(color):
        r, g, b = color[:3]
        return 0.299*r + 0.587*g + 0.114*b

    color_map = dict(zip(nodelist, node_colors))

    for node, text in labels.items():

        if node not in pos:
            continue

        x, y = pos[node]
        col = color_map.get(node, (1, 1, 1))

        txt_color = "white" if luminance(col) < 0.5 else "black"

        ax.text(
            x,
            y,
            text,
            ha="center",
            va="center",
            fontsize=fontsize,
            color=txt_color,
            zorder=50,
        )

def load_positions(excel_file):
    df = pd.read_excel(excel_file, sheet_name="Positions")

    return dict(
        zip(
            df["Node"].astype(int),
            zip(df["x"].astype(float), df["y"].astype(float))
        )
    )

def plot_post_fault_voltages(
        T, fault_edge, Vmag, pos,
        G_all, bus_df,
        Shed=None, system_name=None,
        switches=None
    ):

    (
    nodelist_supplied,
    nodelist_failed,
    labels,
    failure_labels,
    node_colors,
    sm
    ) = prepare_node_plot_data(
            T,
            G_all,
            Vmag,
            pos,
            bus_df,
            Shed=Shed,
    )

    fig, ax = plt.subplots(figsize=(22, 10)) 

    draw_ieee123_zones(system_name)

    draw_fault_symbol(ax, fault_edge, pos)

    nx.draw_networkx_edges(G_all, pos, ax=ax, edge_color="gray", style="dashed", width=1.0, alpha=0.35)

    nx.draw_networkx_edges(T, pos, ax=ax, width=1.6)

    draw_section_edge_labels( G_all, pos, ax=ax, system_name=system_name)

    nx.draw_networkx_nodes(T, pos, ax=ax, nodelist=nodelist_supplied, node_color=node_colors, edgecolors="black", node_size=450 )

    draw_node_labels(ax, pos, labels, nodelist_supplied, node_colors)

    nx.draw_networkx_nodes(G_all, pos, ax=ax, nodelist=nodelist_failed, node_color="black", edgecolors="black", node_size=450)

    nx.draw_networkx_labels(G_all, pos, ax=ax, labels=failure_labels, font_size=7, font_color="white", font_weight="bold")

    nx.draw_networkx_labels(T, pos, ax=ax, labels=labels, font_size=7)

    # draw switches
    if switches is not None:
        draw_switches(G_all, pos, switches)


    cbar = fig.colorbar(sm, ax=ax, fraction=0.075, pad=0.02)
    cbar.set_label("Load shedding (%)")

    cmap = plt.cm.get_cmap()

    # supplied nodes (tuple handled by HandlerTuple)
    supplied_handle = (
        Line2D([0], [0], marker='o', linestyle='None',
               markerfacecolor=cmap(0.2), markeredgecolor='black', markersize=9),

        Line2D([0], [0], marker='o', linestyle='None',
               markerfacecolor=cmap(0.5), markeredgecolor='black', markersize=9),

        Line2D([0], [0], marker='o', linestyle='None',
               markerfacecolor=cmap(0.9), markeredgecolor='black', markersize=9),
    )

    # switch symbols
    switch_closed_handle = Line2D(
        [0], [0],
        marker='o',
        linestyle='None',
        markerfacecolor='green',
        markeredgecolor='white',
        markeredgewidth=1.2,
        markersize=9,
        label='Switch closed'
    )

    switch_open_handle = Line2D(
        [0], [0],
        marker='o',
        linestyle='None',
        markerfacecolor='red',
        markeredgecolor='white',
        markeredgewidth=1.2,
        markersize=9,
        label='Switch open'
    )

    legend_handles = [

        supplied_handle,

        # no-load node
        Line2D(
            [0], [0],
            marker='o',
            linestyle='None',
            markerfacecolor=(0.75, 0.75, 0.75),
            markeredgecolor='black',
            markersize=9,
            label='No-load node'
        ),

        # unsupplied node
        Line2D(
            [0], [0],
            marker='o',
            linestyle='None',
            markerfacecolor='black',
            markeredgecolor='black',
            markersize=9,
            label='Unsupplied node'
        ),

        # energized feeder
        Line2D(
            [0], [0],
            color='black',
            lw=1.6,
            label='Energized feeder'
        ),

        # disconnected feeder
        Line2D(
            [0], [0],
            color='gray',
            lw=1.0,
            linestyle='dashed',
            label='Disconnected feeder'
        ),

        # faulted line
        Line2D(
            [0], [0],
            marker='$⚡$',
            linestyle='None',
            color='red',
            markersize=18,
            label='Faulted line'
        ),

        # switches
        switch_closed_handle,
        switch_open_handle,
    ]

    legend_labels = [
    "Supplied node (color = shedding %)",
    "No-load node",
    "Unsupplied node",
    "Energized feeder",
    "Disconnected feeder",
    "Faulted line",
    "Switch closed",
    "Switch open",
    ]

    ax.legend(
    handles=legend_handles,
    labels=legend_labels,
    handler_map={tuple: HandlerTuple(ndivide=None)},
    loc="lower center",          
    bbox_to_anchor=(0.7, 1.01),  
    ncol=4,                       
    frameon=True,
    framealpha=0.95,
    fontsize=9,
    borderpad=0.8,
    labelspacing=0.8,
    columnspacing=1.6,
    handletextpad=0.6,
)

    xs = [p[0] for p in pos.values()]
    ys = [p[1] for p in pos.values()]

    margin_x = 1
    margin_y = 1

    ax.set_xlim(min(xs)-margin_x, max(xs)+margin_x)
    ax.set_ylim(min(ys)-margin_y, max(ys)+margin_y)


    plt.axis("off")
    plt.tight_layout()
    plt.show()

def draw_ieee123_zones(system_name=None):
    """
    Draw IEEE-123 zone background areas.
    """
    if system_name is None or "IEEE_123" not in system_name:
        return

    ax = plt.gca()

    dx = 1.2
    dy = 1.5

    zones = {
        "Zone 1": (-1.5*dx, -4.5*dy, 7*dx, 6*dy, "lightblue"),
        "Zone 2": (-1.5*dx, 1.5*dy, 7*dx, 6*dy, "lightgreen"),
        "Zone 5": (12.5*dx, 3.5*dy, 6.5*dx, 4*dy, "salmon"),
        "Zone 6": (5.5*dx, -4.5*dy, 13.5*dx, 4*dy, "wheat"),
    }

    for name, (x, y, w, h, color) in zones.items():

        rect = patches.Rectangle(
            (x, y), w, h,
            edgecolor="none",
            facecolor=color,
            alpha=0.25,
            linewidth=1
        )

        ax.add_patch(rect)

        ax.text(
            x + 0.2,
            y + h - 0.5,
            name,
            fontsize=10,
            weight="bold",
            color="black"
        )

    zone3 = [
        (5.5*dx, 0.5*dy),
        (9.5*dx, 0.5*dy),
        (9.5*dx, 4.5*dy),
        (10.5*dx, 4.5*dy),
        (10.5*dx, 5.5*dy),
        (12.5*dx, 5.5*dy),
        (12.5*dx, 7.5*dy),
        (5.5*dx, 7.5*dy),
    ]

    ax.add_patch(Polygon(
        zone3,
        closed=True,
        edgecolor="none",
        facecolor="plum",
        alpha=0.25
    ))

    ax.text(5.7*dx, 7.1*dy, "Zone 3",
            fontsize=10, weight="bold")


    zone4 = [
        (5.5*dx, -0.5*dy),
        (19*dx, -0.5*dy),
        (19*dx, 3.5*dy),
        (12.5*dx, 3.5*dy),
        (12.5*dx, 4.5*dy),
        (12.5*dx, 5.5*dy),
        (10.5*dx, 5.5*dy),
        (10.5*dx, 4.5*dy),
        (9.5*dx, 4.5*dy),
        (9.5*dx, 3.5*dy),
        (9.5*dx, 0.5*dy),
        (5.5*dx, 0.5*dy),
        (5.5*dx, -0.5*dy)
    ]

    ax.add_patch(Polygon(
        zone4,
        closed=True,
        edgecolor="none",
        facecolor="orange",
        alpha=0.25
    ))

    ax.text(5.7*dx, 0.25*dy, "Zone 4",
            fontsize=10, weight="bold")

def draw_section_edge_labels(
        G,
        pos,
        ax,
        system_name=None,
        fontsize=7):

    if system_name in (
        "NEW_CODE/new_systems/IEEE_123Bus.xlsx",
        "NEW_CODE/new_systems/IEEE_123Bus_external_backfeeds.xlsx",
    ):
        offset = 0.25
    else:
        offset = 0.6


    for u, v, data in G.edges(data=True):

        if "section" not in data:
            continue

        if u not in pos or v not in pos:
            continue

        sec_name = data["section"]

        x1, y1 = pos[u]
        x2, y2 = pos[v]

        # midpoint
        xm = (x1 + x2) / 2
        ym = (y1 + y2) / 2

        dx = x2 - x1
        dy = y2 - y1

        L = np.hypot(dx, dy)
        if L == 0:
            continue

        nx = -dy / L
        ny = dx / L

        xt = xm + offset * nx
        yt = ym + offset * ny

        ax.text(
            xt,
            yt,
            sec_name,
            fontsize=fontsize,
            ha="center",
            va="center",
            zorder=30,
        )

def prepare_node_plot_data(
        T,
        G_all,
        Vmag,
        pos,
        bus_df,
        Shed=None,
        cmap_name=None):
    """
    Master preprocessing for node visualization.
    """

    supplied = set(T)
    failed = set(G_all) - supplied

    labels = {}
    for n in supplied:

        v = Vmag.get(n, np.nan)

        text = f"{n+1}"
        if not np.isnan(v):
            text += f"\n{v:.3f}"

        labels[n] = text

    failure_labels = {
        n: f"{n+1}" for n in failed if n in pos
    }

    nodelist_supplied = list(supplied)
    nodelist_failed = list(failed)


    Pload = dict(zip(
        bus_df["Bus"].astype(int) - 1,
        bus_df["P_pu (pu)"].astype(float)
    ))

    NO_LOAD_COLOR = (0.75, 0.75, 0.75, 1.0)

    cmap = cm.get_cmap() if cmap_name is None else cm.get_cmap(cmap_name)
    norm = mcolors.Normalize(vmin=0.0, vmax=100.0)

    shed_percent = []
    node_colors = []

    for n in nodelist_supplied:

        load = Pload.get(n, 0.0)

        if load <= 1e-12:
            shed_percent.append(np.nan)
            node_colors.append(NO_LOAD_COLOR)
            continue

        shed = 0.0 if Shed is None else Shed.get(n, 0.0)

        percent = 100.0 * shed / load
        percent = np.clip(percent, 0.0, 100.0)

        shed_percent.append(percent)
        node_colors.append(cmap(norm(percent)))

    shed_percent = np.array(shed_percent)

    sm = cm.ScalarMappable(norm=norm, cmap=cmap)
    sm.set_array([])

    return (
        nodelist_supplied,
        nodelist_failed,
        labels,
        failure_labels,
        node_colors,
        sm)

def draw_switches(G, pos, switches, size=30):
    """
    Draw switches along edges with constant distance from nodes,
    independent of edge length.
    """

    ax = plt.gca()

    OFFSET = 0.70

    for sw in switches:

        u = sw.get("u")
        v = sw.get("v")

        if None in (u, v):
            continue
        if u not in pos or v not in pos:
            continue

        x1, y1 = pos[u]
        x2, y2 = pos[v]

        dx = x2 - x1
        dy = y2 - y1

        length = np.hypot(dx, dy)
        if length == 0:
            continue

        # enhetsvektor
        ux = dx / length
        uy = dy / length

        placement = sw.get("pos", "middle")

        if placement == "upstream":
            xm = x1 + ux * OFFSET
            ym = y1 + uy * OFFSET

        elif placement == "downstream":
            xm = x2 - ux * OFFSET
            ym = y2 - uy * OFFSET

        else:  # middle
            xm = (x1 + x2) / 2
            ym = (y1 + y2) / 2

        color = "green" if sw.get("status") == "closed" else "red"

        ax.scatter(
            xm,
            ym,
            s=size,
            c=color,
            edgecolors="white",
            linewidths=1.2,
            zorder=30,
        )

    ax.set_aspect("equal")

def draw_fault_symbol(ax, fault_edge, pos,
                      fontsize=24,
                      color="red",
                      symbol="⚡"):

    if fault_edge is None:
        return

    u, v = fault_edge

    if u is None or v is None:
        return

    if u not in pos or v not in pos:
        return

    x1, y1 = pos[u]
    x2, y2 = pos[v]

    # midpoint
    xm = (x1 + x2) / 2
    ym = (y1 + y2) / 2

    ax.text(
        xm,
        ym,
        symbol,
        fontsize=fontsize,
        ha="center",
        va="center",
        color=color,
        zorder=50,
    )
