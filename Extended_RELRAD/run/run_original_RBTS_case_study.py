import matplotlib.pyplot as plt
import numpy as np
from matplotlib.lines import Line2D
from matplotlib.ticker import MaxNLocator

from Extended_RELRAD.run.run_case_studies import run_case_study
from Extended_RELRAD.src.system_setup import build_network

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

def get_base_case(case_label, cases):
    """
    Extract the base case from a list of cases for a given case label.
    """
    base_cases = [
        c for c in cases
        if c[0].lower().startswith("base")
    ]

    if len(base_cases) != 1:
        raise ValueError(
            f"Found {len(base_cases)} Base-cases for case {case_label}: "
            f"{[c[0] for c in base_cases]}"
        )

    name, slack_buses, Vmin, cap_limit, bess_buses, enable_bess_islanding = base_cases[0]

    return (
        f"Base-{case_label}",
        slack_buses,
        Vmin,
        cap_limit,
        bess_buses,
        enable_bess_islanding,
    )

def run_base_A_to_F(
    systems_by_case,
    cases_by_case,
    use_lambda_temp=False,
    plot=True,
    sort_by="Base-A",
    same_load_point_order=True,
    figsize=(16, 8),
    top_n=None,
):
    """
    Run base cases A to F for the given systems and cases.
    """

    details_all = {}
    networks_by_scenario = {}
    all_cases = []

    for case_label, system in systems_by_case.items():
        base_case = get_base_case(
            case_label=case_label,
            cases=cases_by_case[case_label],
        )

        details_one, _ = run_case_study(
            system=system,
            cases=[base_case],
            use_lambda_temp=use_lambda_temp,
            plot=False,
        )

        scenario_name = base_case[0]

        details_all[scenario_name] = details_one[scenario_name]

        networks_by_scenario[scenario_name] = build_network(
            system["path"],
            use_lambda_temp=use_lambda_temp,
        )

        all_cases.append({
            "name": scenario_name,
            "case_label": case_label,
            "slack_buses": base_case[1],
            "Vmin": base_case[2],
            "cap_limit": base_case[3],
            "BESS_buses": base_case[4],
            "enable_bess_islanding": base_case[5],
        })

    if plot:
        fig = plot_base_A_to_F_from_details(
            details=details_all,
            networks_by_scenario=networks_by_scenario,
            sort_by=sort_by,
            same_load_point_order=same_load_point_order,
            figsize=figsize,
            top_n=top_n,
        )
    else:
        fig = None

    return fig

def plot_base_A_to_F_from_details(
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

if __name__ == "__main__":

    systems_by_case = {
        "A": Bus_2_Case_A_system,
        "B": Bus_2_Case_B_system,
        "C": Bus_2_Case_C_system,
        "D": Bus_2_Case_D_system,
        "E": Bus_2_Case_E_system,
        "F": Bus_2_Case_F_system,
        }

    cases_by_case = {
        "A": Bus_2_Case_A_cases,
        "B": Bus_2_Case_B_cases,
        "C": Bus_2_Case_C_cases,
        "D": Bus_2_Case_D_cases,
        "E": Bus_2_Case_E_cases,
        "F": Bus_2_Case_F_cases,
    }

    fig_Bus_2_base_AF = run_base_A_to_F(
        systems_by_case=systems_by_case,
        cases_by_case=cases_by_case,
        use_lambda_temp=False,
        plot=True,
        sort_by="Base-A",
        same_load_point_order=True,
        figsize=(17, 8),
    )

    safe_name = "RBTS_Bus_2_Base_A_to_F"

    fig_Bus_2_base_AF.savefig(
        f"Extended_RELRAD/case_studies_results/{safe_name}.pdf",
        format="pdf",
        bbox_inches="tight",
        pad_inches=0.02,
    )


    # RBTS Bus 4 case studies
    systems_by_case = {
        "A": Bus_4_Case_A_system,
        "B": Bus_4_Case_B_system,
        "C": Bus_4_Case_C_system,
        "D": Bus_4_Case_D_system,
        "E": Bus_4_Case_E_system,
        "F": Bus_4_Case_F_system,
    }

    cases_by_case = {
        "A": Bus_4_Case_A_cases,
        "B": Bus_4_Case_B_cases,
        "C": Bus_4_Case_C_cases,
        "D": Bus_4_Case_D_cases,
        "E": Bus_4_Case_E_cases,
        "F": Bus_4_Case_F_cases,
    }

    fig_Bus_4_base_AF = run_base_A_to_F(
        systems_by_case=systems_by_case,
        cases_by_case=cases_by_case,
        use_lambda_temp=False,
        plot=True,
        sort_by="Base-A",
        same_load_point_order=True,
        figsize=(17, 8),
    )

    safe_name = "RBTS_Bus_4_Base_A_to_F"

    fig_Bus_4_base_AF.savefig(
        f"Extended_RELRAD/case_studies_results/{safe_name}.pdf",
        format="pdf",
        bbox_inches="tight",
        pad_inches=0.02,
    )