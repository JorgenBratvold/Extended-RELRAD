from Extended_RELRAD.run.run_case_studies import run_case_study
from Extended_RELRAD.src.system_setup import build_network
from Extended_RELRAD.src.plotting import plot_RBTS_case_studies

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

def run_RBTS_case_studies(
    systems_by_case,
    cases_by_case,
    use_lambda_temp=False,
    plot=True,
    sort_by="Base-A",
    same_load_point_order=True,
    figsize=(16, 8),
    top_n=None,
    objective="load_shed"
):
    """
    Run base cases A to F for the given systems and cases.
    """

    details_all = {}
    networks_by_scenario = {}
    all_cases = []

    for case_label, system in systems_by_case.items():
        
        base_cases = [
        c for c in cases_by_case[case_label]
        if c[0].lower().startswith("base")
        ]

        if len(base_cases) != 1:
            raise ValueError(
                f"Found {len(base_cases)} Base-cases for case {case_label}: "
                f"{[c[0] for c in base_cases]}"
            )

        name, slack_buses, Vmin, cap_limit, bess_buses, enable_bess_islanding = base_cases[0]

        base_case =  (
            f"Base-{case_label}",
            slack_buses,
            Vmin,
            cap_limit,
            bess_buses,
            enable_bess_islanding,
        )

        details_one, _ = run_case_study(
            system=system,
            cases=[base_case],
            use_lambda_temp=use_lambda_temp,
            plot=False,
            objective=objective,
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
        fig = plot_RBTS_case_studies(
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

    fig_Bus_2_base_AF = run_RBTS_case_studies(
        systems_by_case=systems_by_case,
        cases_by_case=cases_by_case,
        use_lambda_temp=False,
        plot=True,
        sort_by="Base-A",
        same_load_point_order=True,
        figsize=(17, 8),
        top_n=None,
        objective="load_shed"
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

    fig_Bus_4_base_AF = run_RBTS_case_studies(
        systems_by_case=systems_by_case,
        cases_by_case=cases_by_case,
        use_lambda_temp=False,
        plot=True,
        sort_by="Base-A",
        same_load_point_order=True,
        figsize=(17, 8),
        top_n=None,
        objective="load_shed"
    )

    safe_name = "RBTS_Bus_4_Base_A_to_F"

    fig_Bus_4_base_AF.savefig(
        f"Extended_RELRAD/case_studies_results/{safe_name}.pdf",
        format="pdf",
        bbox_inches="tight",
        pad_inches=0.02,
    )