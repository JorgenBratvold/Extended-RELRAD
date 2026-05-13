
import copy
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
import re
from matplotlib.ticker import MaxNLocator
from matplotlib.patches import Rectangle
from tqdm import tqdm

from Extended_RELRAD.src.system_setup import build_network
from Extended_RELRAD.src.RELRAD import run_RELRAD
from Extended_RELRAD.src.plotting import plot_case_study_results

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

'''
Copyright (C) 2026 Jørgen Bratvold.

Part of a GPLv3-licensed thesis implementation derived in part from
RELRAD-software by Sondre Modalsli Aaberg.

Licensed under the GNU General Public License v3.0 or later.
See LICENSE for details.
'''

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

    #selected_case_study = "RBTS Bus 2 case A"
    #selected_case_study = "RBTS Bus 2 case D"
    selected_case_study = "Case Study I: CINELDI single RC"
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
    fig.set_size_inches(14, 9)  # bredde, høyde i inches
    fig.savefig(
       f"Extended_RELRAD/case_studies_results/{safe_name}.pdf",
       format="pdf",
       bbox_inches="tight",
       pad_inches=0.02)


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
    #    f"Extended_RELRAD/case_studies_results/{safe_name}.pdf",
    #    format="pdf",
    #    bbox_inches="tight",
    #    pad_inches=0.02
    #)


