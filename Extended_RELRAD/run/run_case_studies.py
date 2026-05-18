
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
    objective="load_shed",
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
            objective=objective,
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
                "objective": objective,
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

# ENS breakdown/contribution for multiple scenarios in a case study

def print_ENS_pie_values(system, cases, use_lambda_temp=False, case_names=None, objective="load_shed"):
    network = build_network(system["path"], use_lambda_temp=use_lambda_temp)
    Sbase = system["Sbase"]
    comps = ["fault", "isolated", "switching", "shed"]

    for name, slack_buses, Vmin, cap_limit, bess_buses, enable_bess_islanding in cases:
        if case_names is not None and name not in set(case_names):
            continue

        ENS, breakdown, _ = run_RELRAD(
            network=network,
            slack_buses=slack_buses,
            Vmin=Vmin,
            Sbase=Sbase,
            cap_limit=cap_limit,
            BESS_buses=bess_buses,
            enable_bess_islanding=enable_bess_islanding,
            objective=objective,
        )

        totals = {c: sum(breakdown[c].values()) for c in comps}
        total = sum(totals.values())

        print(f"\n{name}")
        print(f"Total ENS = {total:.3f} MWh/yr")
        for c in comps:
            pct = 100 * totals[c] / total if total > 0 else 0.0
            print(f"{c:<10} {totals[c]:>8.3f} MWh/yr   {pct:>5.1f}%")

if __name__ == "__main__":

    case_studies = {

        # All RBTS Bus 2 cases (only A and D shown in the thesis, but all are included here for completeness and potential future use)
        "RBTS Bus 2 case A": {
            "system": Bus_2_Case_A_system,
            "cases": Bus_2_Case_A_cases,
            "objective": "load_shed",
        },
        "RBTS Bus 2 case B": {
            "system": Bus_2_Case_B_system,
            "cases": Bus_2_Case_B_cases,
            "objective": "load_shed",
        },
        "RBTS Bus 2 case C": {
            "system": Bus_2_Case_C_system,
            "cases": Bus_2_Case_C_cases,
            "objective": "load_shed",
        },
        "RBTS Bus 2 case D": {
            "system": Bus_2_Case_D_system,
            "cases": Bus_2_Case_D_cases,
            "objective": "load_shed",
        },
        "RBTS Bus 2 case E": {
            "system": Bus_2_Case_E_system,
            "cases": Bus_2_Case_E_cases,
            "objective": "load_shed",
        },
        "RBTS Bus 2 case F": {
            "system": Bus_2_Case_F_system,
            "cases": Bus_2_Case_F_cases,
            "objective": "load_shed",
        },


        # All CINELDI cases (Case Studies I-V) 
        "Case Study I: CINELDI single RC": {
            "system": Case_Study_I_system,
            "cases": Case_Study_I_cases,
            "objective": "cost",
        },
        "Case Study II: CINELDI with multiple RCs": {
            "system": Case_Study_II_system,
            "cases": Case_Study_II_cases,
            "objective": "cost",
        },
        "Case Study III: CINELDI with single RC and BESS": {
            "system": Case_Study_III_system,
            "cases": Case_Study_III_cases,
            "objective": "cost",
        },
        "Case Study IV: CINELDI with multiple RCs and BESS": {
            "system": Case_Study_IV_system,
            "cases": Case_Study_IV_cases,
            "objective": "cost",
        },
        "Case Study V: CINELDI with single RC and BESS, islanding contribution": {
            "system": Case_Study_V_system,
            "cases": Case_Study_V_cases,
            "objective": "cost",
        },


        # All RBTS Bus 4 cases (Not used in the thesis, but included here for completeness and potential future use)
        "RBTS Bus 4 case A": {
            "system": Bus_4_Case_A_system,
            "cases": Bus_4_Case_A_cases,
            "objective": "load_shed",
        },
        "RBTS Bus 4 case B": {
            "system": Bus_4_Case_B_system,
            "cases": Bus_4_Case_B_cases,
            "objective": "load_shed",
        },
        "RBTS Bus 4 case C": {
            "system": Bus_4_Case_C_system,
            "cases": Bus_4_Case_C_cases,
            "objective": "load_shed",
        },
        "RBTS Bus 4 case D": {
            "system": Bus_4_Case_D_system,
            "cases": Bus_4_Case_D_cases,
            "objective": "load_shed",
        },
        "RBTS Bus 4 case E": {
            "system": Bus_4_Case_E_system,
            "cases": Bus_4_Case_E_cases,
            "objective": "load_shed",
        },
        "RBTS Bus 4 case F": {
            "system": Bus_4_Case_F_system,
            "cases": Bus_4_Case_F_cases,
            "objective": "load_shed",
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
       same_load_point_order=True,
       objective=case_studies[selected_case_study]["objective"],
    )
    #
    #safe_name = re.sub(r"\s+", "_", selected_case_study.strip())
    #fig.set_size_inches(14, 9)  # bredde, høyde i inches
    #fig.savefig(
    #   f"Extended_RELRAD/case_studies_results/{safe_name}.pdf",
    #   format="pdf",
    #   bbox_inches="tight",
    #   pad_inches=0.02)


    ## ENS breakdown case study for CINELDI single RC cases
    #selected_breakdown_case_study = "Case Study I: CINELDI single RC"
    #print_ENS_pie_values(
    #    system=case_studies[selected_breakdown_case_study]["system"],
    #    cases=case_studies[selected_breakdown_case_study]["cases"],
    #    use_lambda_temp=False,
    #    case_names=["Base-RC62", "V095-Cap2-RC62"],
    #    objective=case_studies[selected_breakdown_case_study]["objective"],
    #)

