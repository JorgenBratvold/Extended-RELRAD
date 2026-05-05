
import copy
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from collections import OrderedDict
import re
from matplotlib.ticker import MaxNLocator
from matplotlib.legend_handler import HandlerBase
from matplotlib.patches import Rectangle
from tqdm import tqdm


from Extended_RELRAD.src.system_setup import build_network
from Extended_RELRAD.src.RELRAD import run_RELRAD

# CINELDI case studies
from Extended_RELRAD.case_studies.CINELDI_case_studies.Case_Study_I_single_RC import Case_Study_I_system, Case_Study_I_cases
from Extended_RELRAD.case_studies.CINELDI_case_studies.Case_Study_II_multiple_RC import Case_Study_II_system, Case_Study_II_cases
from Extended_RELRAD.case_studies.CINELDI_case_studies.Case_Study_III_single_RC_BESS import Case_Study_III_system, Case_Study_III_cases
from Extended_RELRAD.case_studies.CINELDI_case_studies.Case_Study_IV_multiple_RC_BESS import Case_Study_IV_system, Case_Study_IV_cases
from Extended_RELRAD.case_studies.CINELDI_case_studies.Case_Study_V_single_RC_BESS_island import Case_Study_V_system, Case_Study_V_cases

# RBTS Bus 2 case studies
from Extended_RELRAD.case_studies.RBTS_Bus_2_case_studies.Bus_2_Case_A import Bus_2_Case_A_system, Bus_2_Case_A_cases
from Extended_RELRAD.case_studies.RBTS_Bus_2_case_studies.Bus_2_Case_B import Bus_2_Case_B_system, Bus_2_Case_B_cases
from Extended_RELRAD.case_studies.RBTS_Bus_2_case_studies.Bus_2_Case_C import Bus_2_Case_C_system, Bus_2_Case_C_cases
from Extended_RELRAD.case_studies.RBTS_Bus_2_case_studies.Bus_2_Case_D import Bus_2_Case_D_system, Bus_2_Case_D_cases
from Extended_RELRAD.case_studies.RBTS_Bus_2_case_studies.Bus_2_Case_E import Bus_2_Case_E_system, Bus_2_Case_E_cases
from Extended_RELRAD.case_studies.RBTS_Bus_2_case_studies.Bus_2_Case_F import Bus_2_Case_F_system, Bus_2_Case_F_cases

# RBTS Bus 4 case studies
from Extended_RELRAD.case_studies.RBTS_Bus_4_case_studies.Bus_4_Case_A import Bus_4_Case_A_system, Bus_4_Case_A_cases
from Extended_RELRAD.case_studies.RBTS_Bus_4_case_studies.Bus_4_Case_B import Bus_4_Case_B_system, Bus_4_Case_B_cases
from Extended_RELRAD.case_studies.RBTS_Bus_4_case_studies.Bus_4_Case_C import Bus_4_Case_C_system, Bus_4_Case_C_cases
from Extended_RELRAD.case_studies.RBTS_Bus_4_case_studies.Bus_4_Case_D import Bus_4_Case_D_system, Bus_4_Case_D_cases
from Extended_RELRAD.case_studies.RBTS_Bus_4_case_studies.Bus_4_Case_E import Bus_4_Case_E_system, Bus_4_Case_E_cases
from Extended_RELRAD.case_studies.RBTS_Bus_4_case_studies.Bus_4_Case_F import Bus_4_Case_F_system, Bus_4_Case_F_cases


def run_case_study(
    system,
    cases,
    use_lambda_temp=False,
    plot=False,
    sort_by=None,
    same_load_point_order=True,
):
    """
    Run a case study with multiple scenarios and optionally plot the results.

    args:
        system: Dictionary with system information, including the data path and Sbase.
        cases: List of case definitions. Each case is expected to contain:
            name, slack_buses, Vmin, cap_limit, BESS_buses, and enable_bess_islanding.
        use_lambda_temp: If True, include temporary failure rates in addition to
            permanent failure rates.
        plot: If True, plot ENS per load point and aggregated ENS.
        sort_by: Scenario name used to rank load points in the plot. If None, the
            first scenario in cases is used.
        same_load_point_order: If True, all scenarios will be plotted with load points in the same order, determined by the sort_by scenario. If False, each scenario will be plotted with load points sorted by their own ENS values.

    returns:
        details: Dictionary with detailed results for each scenario, including:
            - ENS_per_bus
            - ENS_breakdown_per_bus
            - contingency_results
            - total_ENS
            - total_ENS_breakdown
            - inputs
    """

    network = build_network(
        system["path"],
        use_lambda_temp=use_lambda_temp,
    )

    Sbase = system["Sbase"]

    all_cases = [
        {
            "name": name,
            "slack_buses": slack_buses,
            "Vmin": Vmin,
            "cap_limit": cap_limit,
            "BESS_buses": bess_buses,
            "enable_bess_islanding": enable_bess_islanding,
        }
        for name, slack_buses, Vmin, cap_limit, bess_buses, enable_bess_islanding in cases
    ]

    details = {}

    for i, sc in enumerate(
        tqdm(
            all_cases,
            desc="Running case study",
            unit="scenario",
            ncols=100,
        ),
        start=1,
    ):
        name = sc.get("name", f"Scenario {i}")

        ENS, ENS_breakdown_total, contingency_results = run_RELRAD(
            network=network,
            slack_buses=sc["slack_buses"],
            Vmin=sc["Vmin"],
            Sbase=Sbase,
            cap_limit=sc["cap_limit"],
            BESS_buses=sc.get("BESS_buses", {}),
            enable_bess_islanding=sc.get("enable_bess_islanding", False),
        )

        details[name] = {
            "ENS_per_bus": copy.deepcopy(ENS),
            "ENS_breakdown_per_bus": copy.deepcopy(ENS_breakdown_total),
            "contingency_results": copy.deepcopy(contingency_results),
            "total_ENS": float(sum(ENS.values())),
            "total_ENS_breakdown": {
                "fault": float(sum(ENS_breakdown_total["fault"].values())),
                "isolated": float(sum(ENS_breakdown_total["isolated"].values())),
                "switching": float(sum(ENS_breakdown_total["switching"].values())),
                "shed": float(sum(ENS_breakdown_total["shed"].values())),
            },
            "inputs": {
                "slack_buses": sc["slack_buses"],
                "Vmin": sc["Vmin"],
                "cap_limit": sc["cap_limit"],
                "BESS_buses": copy.deepcopy(sc.get("BESS_buses", {})),
                "enable_bess_islanding": sc.get("enable_bess_islanding", False),
            },
        }

    if plot:
        if sort_by is None:
            sort_by = all_cases[0]["name"]

        fig = plot_case_study_results(
            details=details,
            network=network,
            all_cases=all_cases,
            sort_by=sort_by,
            same_load_point_order=same_load_point_order,
        )
    else:
        fig = None

    return details, fig

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

# Plot ENS breakdown/contribution for multiple scenarios in a case study

def run_ENS_breakdown_case_study(
    system,
    cases,
    use_lambda_temp=False,
    sort_by=None,
    sort_desc=True,
    top_n=20,
    plot=True,
    case_names=None,
):
    network = build_network(system["path"], use_lambda_temp=use_lambda_temp)
    Sbase = system["Sbase"]

    scenarios = [
        {
            "name": name,
            "slack_buses": slack_buses,
            "Vmin": Vmin,
            "cap_limit": cap_limit,
            "BESS_buses": bess_buses,
            "enable_bess_islanding": enable_bess_islanding,
        }
        for name, slack_buses, Vmin, cap_limit, bess_buses, enable_bess_islanding in cases
    ]

    if case_names is not None:
        scenarios = [sc for sc in scenarios if sc["name"] in set(case_names)]

    if not scenarios:
        raise ValueError("Ingen cases/scenarioer ble valgt.")

    load_buses = sorted(
        b for b, data in network["buses"].items()
        if max(data["P_load"], 0.0) > 1e-9
    )

    components = ["fault", "isolated", "switching", "shed"]
    results = []

    for sc in scenarios:
        ENS, breakdown, contingencies = run_RELRAD(
            network=network,
            slack_buses=sc["slack_buses"],
            Vmin=sc["Vmin"],
            Sbase=Sbase,
            cap_limit=sc["cap_limit"],
            BESS_buses=sc.get("BESS_buses", {}),
            enable_bess_islanding=sc.get("enable_bess_islanding", False),
        )

        df = pd.DataFrame({
            "bus": [b + 1 for b in load_buses],
            **{
                comp: [breakdown[comp].get(b, 0.0) for b in load_buses]
                for comp in components
            },
        })
        df["total_ENS"] = df[components].sum(axis=1)

        results.append({
            "name": sc["name"],
            "df": df,
            "totals": {comp: float(df[comp].sum()) for comp in components}
                      | {"total": float(df["total_ENS"].sum())},
            "inputs": {
                "slack_buses": sc["slack_buses"],
                "Vmin": sc["Vmin"],
                "cap_limit": sc["cap_limit"],
            },
            "ENS_per_bus": copy.deepcopy(ENS),
            "ENS_breakdown_per_bus": copy.deepcopy(breakdown),
            "contingency_results": copy.deepcopy(contingencies),
        })

    if sort_by is None:
        sort_by = results[0]["name"]

    ref = next((r for r in results if r["name"] == sort_by), None)
    if ref is None:
        raise ValueError(
            f"sort_by='{sort_by}' does not exist. Choose one of: {[r['name'] for r in results]}"
        )

    base_df = ref["df"].sort_values(
        "total_ENS" if sort_desc else "bus",
        ascending=not sort_desc,
    )

    if top_n is not None:
        base_df = base_df.head(top_n)

    bus_order = base_df["bus"].tolist()

    for r in results:
        r["df"] = (
            r["df"]
            .set_index("bus")
            .reindex(bus_order)
            .fillna(0.0)
            .reset_index()
        )
        r["df"]["total_ENS"] = r["df"][components].sum(axis=1)

    details = {
        r["name"]: {
            "df": r["df"].copy(),
            "totals": copy.deepcopy(r["totals"]),
            "inputs": copy.deepcopy(r["inputs"]),
            "ENS_per_bus": copy.deepcopy(r["ENS_per_bus"]),
            "ENS_breakdown_per_bus": copy.deepcopy(r["ENS_breakdown_per_bus"]),
            "contingency_results": copy.deepcopy(r["contingency_results"]),
        }
        for r in results
    }

    if not plot:
        return details, None

    colors = {
        "fault": "#5B8DB8",
        "isolated": "#E6A04B",
        "switching": "#6BAA75",
        "shed": "#C96B72",
    }
    labels = {
        "fault": "Fault",
        "isolated": "Isolated",
        "switching": "Switching",
        "shed": "Shed",
    }
    hatches = ["", "//", "\\\\", "xx", "..", "++", "--"]

    plt.rcParams.update({
        "figure.facecolor": "white",
        "axes.facecolor": "white",
        "savefig.facecolor": "white",
        "font.size": 12,
        "axes.labelsize": 13,
        "xtick.labelsize": 11,
        "ytick.labelsize": 11,
        "legend.fontsize": 11,
        "axes.edgecolor": "black",
        "axes.linewidth": 1.0,
        "xtick.color": "black",
        "ytick.color": "black",
        "axes.labelcolor": "black",
        "text.color": "black",
        "legend.frameon": True,
        "legend.facecolor": "white",
        "legend.edgecolor": "#BDBDBD",
        "legend.framealpha": 1.0,
        "legend.fancybox": True,
        "hatch.linewidth": 0.8,
        "pdf.fonttype": 42,
        "ps.fonttype": 42,
    })

    plot_results = sorted(results, key=lambda r: r["totals"]["total"])
    x = np.arange(len(bus_order))
    n_sc = len(plot_results)
    width = 0.58 if n_sc == 1 else min(0.26, 0.86 / n_sc * 0.94)
    offsets = (np.arange(n_sc) - (n_sc - 1) / 2) * width * 1.08

    fig, ax = plt.subplots(figsize=(20, 9))
    ymax = 0.0

    for i, r in enumerate(plot_results):
        bottom = np.zeros(len(x))
        hatch = hatches[i % len(hatches)]

        for comp in components:
            vals = r["df"][comp].to_numpy()
            ax.bar(
                x + offsets[i],
                vals,
                width=width,
                bottom=bottom,
                color=colors[comp],
                hatch=hatch,
                edgecolor="black",
                linewidth=0.55,
                zorder=3,
            )
            bottom += vals

        ymax = max(ymax, float(bottom.max()) if len(bottom) else 0.0)

    ax.set_xticks(x)
    ax.set_xticklabels([str(b) for b in bus_order], rotation=90)
    ax.set_xlabel(f"Load points ranked by {sort_by}", labelpad=10)
    ax.set_ylabel("ENS breakdown [MWh/year]", labelpad=10)
    ax.set_ylim(0, max(ymax * 1.14, 1e-9))
    ax.yaxis.set_major_locator(MaxNLocator(nbins=7))
    ax.grid(axis="y", color="#D0D0D0", linewidth=0.9, alpha=0.75)
    ax.set_axisbelow(True)

    if len(x):
        ax.set_xlim(-0.65, x[-1] + 0.65)

    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.spines["left"].set_linewidth(1.1)
    ax.spines["bottom"].set_linewidth(1.1)

    handles = [
        Rectangle((0, 0), 1, 1, facecolor=colors[c], edgecolor="black", linewidth=0.7, label=labels[c])
        for c in components
    ] + [
        Line2D([], [], linestyle="", marker="", label="   ")
    ] + [
        Rectangle(
            (0, 0),
            1,
            1,
            facecolor="white",
            hatch=hatches[i % len(hatches)],
            edgecolor="black",
            linewidth=0.8,
            label=r["name"],
        )
        for i, r in enumerate(plot_results)
    ]

    legend = ax.legend(
        handles=handles,
        loc="upper center",
        bbox_to_anchor=(0.5, 0.98),
        ncol=min(len(handles), 8),
        frameon=True,
        fancybox=True,
        borderpad=0.9,
        handlelength=2.0,
        handleheight=1.0,
        handletextpad=0.65,
        columnspacing=1.35,
    )

    frame = legend.get_frame()
    frame.set_facecolor("white")
    frame.set_edgecolor("#CFCFCF")
    frame.set_linewidth(1.1)
    frame.set_alpha(1.0)

    plt.tight_layout(rect=[0.01, 0.01, 0.99, 0.91])
    plt.show()

    return details, fig

if __name__ == "__main__":

    case_studies = {

        # All RBTS Bus 2 cases (only A and D shown in the thesis, but all are included here for completeness and potential future use)
        "RBTS Bus 2 case A": {
            "system": Bus_2_Case_A_system,
            "cases": Bus_2_Case_A_cases,
        },
        "RBTS Bus 2 case B": {
            "system": Bus_2_Case_B_system,
            "cases": Bus_2_Case_B_cases,
        },
        "RBTS Bus 2 case C": {
            "system": Bus_2_Case_C_system,
            "cases": Bus_2_Case_C_cases,
        },
        "RBTS Bus 2 case D": {
            "system": Bus_2_Case_D_system,
            "cases": Bus_2_Case_D_cases,
        },
        "RBTS Bus 2 case E": {
            "system": Bus_2_Case_E_system,
            "cases": Bus_2_Case_E_cases,
        },
        "RBTS Bus 2 case F": {
            "system": Bus_2_Case_F_system,
            "cases": Bus_2_Case_F_cases,
        },


        # All CINELDI cases (Case Studies I-V) 
        "Case Study I: CINELDI single RC": {
            "system": Case_Study_I_system,
            "cases": Case_Study_I_cases,
        },
        "Case Study II: CINELDI with multiple RCs": {
            "system": Case_Study_II_system,
            "cases": Case_Study_II_cases,
        },
        "Case Study III: CINELDI with single RC and BESS": {
            "system": Case_Study_III_system,
            "cases": Case_Study_III_cases,
        },
        "Case Study IV: CINELDI with multiple RCs and BESS": {
            "system": Case_Study_IV_system,
            "cases": Case_Study_IV_cases,
        },
        "Case Study V: CINELDI with single RC and BESS, islanding contribution": {
            "system": Case_Study_V_system,
            "cases": Case_Study_V_cases,
        },


        # All RBTS Bus 4 cases (Not used in the thesis, but included here for completeness and potential future use)
        "RBTS Bus 4 case A": {
            "system": Bus_4_Case_A_system,
            "cases": Bus_4_Case_A_cases,
        },
        "RBTS Bus 4 case B": {
            "system": Bus_4_Case_B_system,
            "cases": Bus_4_Case_B_cases,
        },
        "RBTS Bus 4 case C": {
            "system": Bus_4_Case_C_system,
            "cases": Bus_4_Case_C_cases,
        },
        "RBTS Bus 4 case D": {
            "system": Bus_4_Case_D_system,
            "cases": Bus_4_Case_D_cases,
        },
        "RBTS Bus 4 case E": {
            "system": Bus_4_Case_E_system,
            "cases": Bus_4_Case_E_cases,
        },
        "RBTS Bus 4 case F": {
            "system": Bus_4_Case_F_system,
            "cases": Bus_4_Case_F_cases,
        },
    }

    # All case studies used in the thesis:
    # (other case studes are included in the case_studies dictionary above for completeness and
    # potential future use, but only the ones listed below were actually used in the thesis)

    selected_case_study = "RBTS Bus 2 case A"
    #selected_case_study = "RBTS Bus 2 case D"
    #selected_case_study = "Case Study I: CINELDI single RC"
    #selected_case_study = "Case Study II: CINELDI with multiple RCs"
    #selected_case_study = "Case Study III: CINELDI with single RC and BESS"
    #selected_case_study = "Case Study IV: CINELDI with multiple RCs and BESS"
    #selected_case_study = "Case Study V: CINELDI with single RC and BESS, islanding contribution"

    details, fig = run_case_study(
       system=case_studies[selected_case_study]["system"],
       cases=case_studies[selected_case_study]["cases"],
       plot=True,
       sort_by=None,
       same_load_point_order=True)
    
    safe_name = re.sub(r"\s+", "_", selected_case_study.strip())
    fig.savefig(
       f"RELRAD_with_constraints/case_studies_results/{safe_name}.pdf",
       format="pdf",
       bbox_inches="tight",
       pad_inches=0.02
    )


    ## ENS breakdown case study for CINELDI single RC cases
    #selected_breakdown_case_study = "Case Study I: CINELDI single RC"
    #details, fig = run_ENS_breakdown_case_study(
    #    system=case_studies[selected_breakdown_case_study]["system"],
    #    cases=case_studies[selected_breakdown_case_study]["cases"],
    #    case_names=["Base-RC62", "V095-Cap2-RC62"], sort_by="Base-RC62", plot=True,
    #    top_n=None,
    #)
#
    #safe_name = "ENS_breakdown"
#
    #fig.savefig(
    #    f"RELRAD_with_constraints/case_studies_results/{safe_name}.pdf",
    #    format="pdf",
    #    bbox_inches="tight",
    #    pad_inches=0.02
    #)


