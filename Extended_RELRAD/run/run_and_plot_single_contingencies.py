
from Extended_RELRAD.src.load_flow import lin_dist_flow
from Extended_RELRAD.src.system_setup import build_network
from Extended_RELRAD.src.utils import find_reachable_buses
from Extended_RELRAD.src.plotting import plot_network
from Extended_RELRAD.src.RELRAD import run_single_contingency

'''
Copyright (C) 2026 Jørgen Bratvold.

Part of a GPLv3-licensed thesis implementation derived in part from
RELRAD-software by Sondre Modalsli Aaberg.

Licensed under the GNU General Public License v3.0 or later.
See LICENSE for details.
'''

# Single contingency analysis and visualization

def run_and_plot_contingency(
    system,
    line_id,
    Vmin=0.95,
    cap_limit=0.1,
    BESS_buses=None,
    use_lambda_temp=False,
    plot=True,
    enable_bess_islanding=False,
):
    """
    Run a single contingency analysis and plot the results.

    args:
        system: A dictionary containing the system data and parameters.
        line_id: The ID of the line to be faulted (1-indexed).
        Vmin: The minimum voltage limit in per unit.
        cap_limit: The capacity limit for the reserve connections in per unit.
        BESS_buses: A dictionary mapping bus numbers to their BESS parameters  (energy capacity, power capacity, state of charge, efficiency).
        use_lambda_temp: Whether to use temporary failure rates for the lines.
        plot: Whether to plot the results.
        enable_bess_islanding: Whether to enable BESS islanding in the analysis.
    
    returns:
        None. Plots the results of the contingency analysis.
    """

    network = build_network(system["path"], use_lambda_temp=use_lambda_temp)

    Sbase = system["Sbase"]

    slack_buses = system["default_slack_buses"]
    slack_buses = [slack - 1 for slack in slack_buses]
    buses = network["buses"]

    _, _, children_mapping = find_reachable_buses(
        slack_buses[0],
        buses,
        network["lines"],
        faulted_buses=None)

    V_pre_mapping, _, _ = lin_dist_flow(network, slack_buses[0], children_mapping)

    _, _, contingency_result = run_single_contingency(
        line_id=line_id,
        network=network,
        slack_buses=slack_buses,
        Vmin=Vmin,
        Sbase=Sbase,
        cap_limit=cap_limit,
        V_pre_mapping=V_pre_mapping,
        BESS_buses=BESS_buses or {},
        build_results=True,
        enable_bess_islanding=enable_bess_islanding,
    )

    if plot and contingency_result is not None:
        fig, ax = plot_network(
            pos=network["positions"],
            lines=contingency_result["lines"],
            voltages=contingency_result["voltages"],
            energized_buses=contingency_result["energized_buses"],
            buses=network["buses"],
            switching_owner=contingency_result["switching_owner"],
            shed_nodes=contingency_result["shed_nodes"],
            slack_buses=contingency_result["slack_buses"],
            BESS_buses=contingency_result.get("BESS_buses", {}),
            BESS_power=contingency_result.get("BESS_power", {}),
            supply_type_mapping=contingency_result.get("supply_type_mapping", {}),
            Pflows=contingency_result["Pflows"],
            parent=contingency_result["parent"],
            Sbase=Sbase,
            show=True,
        )

        return fig, ax

if __name__ == "__main__":

    contingency_id = 2  # Contingency on line 2 (between bus 2 and bus 3)

    #Case Study I: V095-Cap2-RC62, contingency on line 2 (between bus 2 and bus 3)
    from Extended_RELRAD.case_studies.CINELDI_case_studies.Case_Study_I_single_RC import Case_Study_I_system
    fig, ax = run_and_plot_contingency(Case_Study_I_system, line_id=contingency_id, Vmin=0.95, cap_limit=0.2, plot=True)
    name = "Case-Study-I-V095-Cap2-RC62-line-2"
    fig.set_size_inches(14, 9)
    fig.savefig(
    f"Extended_RELRAD/contingency_plots/{name}.pdf",
    dpi=300,
    bbox_inches="tight"
    )
    

    # CINELDI with multiple RCs case study
    from Extended_RELRAD.case_studies.CINELDI_case_studies.Case_Study_II_multiple_RC import Case_Study_II_system
    #fig, ax = run_and_plot_contingency(Case_Study_II_system, line_id=contingency_id, Vmin=0.95, cap_limit=0.35, plot=True)

    # Case Study III: V095-Cap1-RC62-AllBESS-grid
    from Extended_RELRAD.case_studies.CINELDI_case_studies.Case_Study_III_single_RC_BESS import Case_Study_III_system, BESS_121
    fig, ax = run_and_plot_contingency(Case_Study_III_system, line_id=contingency_id, Vmin=0.95, cap_limit=0.1, plot=True, BESS_buses=BESS_121, enable_bess_islanding=False)
    name = "Case-Study-III-V095-Cap1-RC62-AllBESS-grid-line-2"
    fig.set_size_inches(14, 9)
    fig.savefig(
    f"Extended_RELRAD/contingency_plots/{name}.pdf",
    dpi=300,
    bbox_inches="tight"
    )
    
    # Case Study IV: V095-Cap2-AllRC 
    from Extended_RELRAD.case_studies.CINELDI_case_studies.Case_Study_IV_multiple_RC_BESS import Case_Study_IV_system, BESS_all
    fig, ax = run_and_plot_contingency(Case_Study_IV_system, line_id=contingency_id, Vmin=0.95, cap_limit=0.20, plot=True, enable_bess_islanding=False)
    name = "Case-Study-IV-V095-Cap2-AllRC-line-2"
    fig.set_size_inches(14, 9)
    fig.savefig(
    f"Extended_RELRAD/contingency_plots/{name}.pdf",
    dpi=300,
    bbox_inches="tight"
    )


    # Case Study IV: V095-Cap2-AllRC-AllBESS-grid
    from Extended_RELRAD.case_studies.CINELDI_case_studies.Case_Study_IV_multiple_RC_BESS import Case_Study_IV_system, BESS_all
    fig, ax = run_and_plot_contingency(Case_Study_IV_system, line_id=contingency_id, Vmin=0.95, cap_limit=0.20, plot=True, BESS_buses=BESS_all, enable_bess_islanding=False)
    name = "Case-Study-IV-V095-Cap2-AllRC-AllBESS-grid-line-2"
    fig.set_size_inches(14, 9)
    fig.savefig(
    f"Extended_RELRAD/contingency_plots/{name}.pdf",
    dpi=300,
    bbox_inches="tight"
    )
    
    # Case Study IV: V095-Cap3-AllRC-AllBESS-grid
    from Extended_RELRAD.case_studies.CINELDI_case_studies.Case_Study_IV_multiple_RC_BESS import Case_Study_IV_system, BESS_all
    fig, ax = run_and_plot_contingency(Case_Study_IV_system, line_id=contingency_id, Vmin=0.95, cap_limit=0.30, plot=True, BESS_buses=BESS_all, enable_bess_islanding=False)
    name = "Case-Study-IV-V095-Cap3-AllRC-AllBESS-grid-line-2"
    fig.set_size_inches(14, 9)
    fig.savefig(
    f"Extended_RELRAD/contingency_plots/{name}.pdf",
    dpi=300,
    bbox_inches="tight"
    )
    

    # Case Study V: V095-Cap1-RC62-AllBESS-island
    from Extended_RELRAD.case_studies.CINELDI_case_studies.Case_Study_V_single_RC_BESS_island import Case_Study_V_system, BESS_all
    fig, ax = run_and_plot_contingency(Case_Study_V_system, line_id=contingency_id, Vmin=0.95, cap_limit=0.1, plot=True, BESS_buses=BESS_all, enable_bess_islanding=True)
    name = "Case-Study-V-V095-Cap1-RC62-AllBESS-island-line-2"
    fig.set_size_inches(14, 9)
    fig.savefig(
    f"Extended_RELRAD/contingency_plots/{name}.pdf",
    dpi=300,
    bbox_inches="tight"
    )
    

    from Extended_RELRAD.case_studies.RBTS_Bus_2_case_studies.Bus_2_Case_A import Bus_2_Case_A_system
    #fig, ax = run_and_plot_contingency(Bus_2_Case_A_system, line_id=1, Vmin = 0.0, cap_limit=0.2, plot=True)

    from Extended_RELRAD.case_studies.RBTS_Bus_2_case_studies.Bus_2_Case_D import Bus_2_Case_D_system 
    #fig, ax = run_and_plot_contingency(Bus_2_Case_D_system, line_id=10, Vmin = 0.9, cap_limit=1000, plot=True)
    
    # IEEE 123 Bus test system - just for testing during development, not part of any case study 
    from Extended_RELRAD.case_studies.IEEE_123_Bus_case_studies.IEEE_123_Bus import IEEE_123_Bus_system
    #fig, ax = run_and_plot_contingency(IEEE_123_Bus_system, line_id=40, Vmin=0.80, cap_limit=3.5, plot=True)

    # RBTS Bus 4 case A 
    from Extended_RELRAD.case_studies.RBTS_Bus_4_case_studies.Bus_4_Case_A import Bus_4_Case_A_system
    #fig, ax = run_and_plot_contingency(Bus_4_Case_A_system, line_id=1, Vmin = None, cap_limit=1000, plot=True)

    # RBTS Bus 4 case B 
    from Extended_RELRAD.case_studies.RBTS_Bus_4_case_studies.Bus_4_Case_B import Bus_4_Case_B_system
    #fig, ax = run_and_plot_contingency(Bus_4_Case_B_system, line_id=1, Vmin = None, cap_limit=1000, plot=True)


    

    
    