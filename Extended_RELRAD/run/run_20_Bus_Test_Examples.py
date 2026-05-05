from Extended_RELRAD.run.run_and_plot_single_contingencies import run_and_plot_contingency

contingency_id = 3  # Same contingency for all examples in the thesis, but can be changed to test different contingencies

Example_20_Bus_Test_system = {
    # Path to the Excel file containing the system data
    "path": "Extended_RELRAD/compatible_systems/20BusTest.xlsx",

    # Default slack buses used in the power flow analysis
    "default_slack_buses": [1, 9],

    # System base power in MVA
    "Sbase": 10
}

Example_20_Bus_Test_system_multi_RC = {
    # Path to the Excel file containing the system data
    "path": "Extended_RELRAD/compatible_systems/20BusTest.xlsx",

    # Default slack buses used in the power flow analysis
    "default_slack_buses": [1, 9, 16],

    # System base power in MVA
    "Sbase": 10
}


# Example 1

run_and_plot_contingency(Example_20_Bus_Test_system, contingency_id, Vmin=None, cap_limit=None, plot=True)


# Example 2 - Lower voltage limit, infinite reserve capacity, no BESS, single RC at bus 9

#  Vmin = 0.94 p.u.                          
run_and_plot_contingency(Example_20_Bus_Test_system, contingency_id, Vmin=0.94, cap_limit=1000, plot=True)
# Vmin = 0.95 p.u.
run_and_plot_contingency(Example_20_Bus_Test_system, contingency_id, Vmin=0.95, cap_limit=1000, plot=True)
# Vmin = 0.96 p.u.
run_and_plot_contingency(Example_20_Bus_Test_system, contingency_id, Vmin=0.96, cap_limit=1000, plot=True)


# Example 3 - No voltage limit, limited reserve capacity, no BESS, single RC at bus 9

# cap_limit = 0.2 p.u. (2 MW)
run_and_plot_contingency(Example_20_Bus_Test_system, contingency_id, Vmin=0.0, cap_limit=0.2, plot=True)
# cap_limit = 0.1 p.u. (1 MW)
run_and_plot_contingency(Example_20_Bus_Test_system, contingency_id, Vmin=0.0, cap_limit=0.1, plot=True)
# cap_limit = 0.05 p.u. (0.5 MW)
run_and_plot_contingency(Example_20_Bus_Test_system, contingency_id, Vmin=0.0, cap_limit=0.05, plot=True)


# Example 4 - No voltage limit, limited reserve capacity, no BESS, RC at bus 9 and bus 16

# cap_limit = 0.2 p.u. (2 MW)
run_and_plot_contingency(Example_20_Bus_Test_system_multi_RC, contingency_id, Vmin=0.0, cap_limit=0.2, plot=True)
# cap_limit = 0.1 p.u. (1 MW)
run_and_plot_contingency(Example_20_Bus_Test_system_multi_RC, contingency_id, Vmin=0.0, cap_limit=0.1, plot=True)
# cap_limit = 0.05 p.u. (0.5 MW)
run_and_plot_contingency(Example_20_Bus_Test_system_multi_RC, contingency_id, Vmin=0.0, cap_limit=0.05, plot=True)


# Example 5 - BESS as bus 20, RC at bus 9

# BESS unit
BESS_buses = {
    # bus    Energy capacity [p.u.]    Maximum power capacity [p.u.]    State of charge [-]    Efficiency [-]
    20: {   "E": 0.15,                 "P": 0.05,                       "SoC": 0.5,            "eta": 0.94**2},
}

# Vmin = 0.0 p.u., cap_limit = inf.
run_and_plot_contingency(Example_20_Bus_Test_system, contingency_id, Vmin=0.0, cap_limit=1000, plot=True, BESS_buses=BESS_buses)
# Vmin = 0.0 p.u., cap_limit = 0.1 p.u.
run_and_plot_contingency(Example_20_Bus_Test_system, contingency_id, Vmin=0.0, cap_limit=0.1, plot=True, BESS_buses=BESS_buses)  
# Vmin = 0.95 p.u., cap_limit = inf.
run_and_plot_contingency(Example_20_Bus_Test_system, contingency_id, Vmin=0.95, cap_limit=1000, plot=True, BESS_buses=BESS_buses)


# Example 6 - Single RC with BESS at bus 20, with focus on BESS islanding contribution

# Vmin = 0.95 p.u., cap_limit = 0.05 p.u., allow BESS islanding with SoC = 0.25 (25% of energy capacity available)
BESS_buses[20]["SoC"] = 0.25
run_and_plot_contingency(Example_20_Bus_Test_system, contingency_id, Vmin=0.95, cap_limit=0.05, plot=True, BESS_buses=BESS_buses, enable_bess_islanding=True)  
# Vmin = 0.95 p.u., cap_limit = 0.05 p.u., allow BESS islanding with SoC = 0.5 (50% of energy capacity available)
BESS_buses[20]["SoC"] = 0.5
run_and_plot_contingency(Example_20_Bus_Test_system, contingency_id, Vmin=0.95, cap_limit=0.05, plot=True, BESS_buses=BESS_buses, enable_bess_islanding=True)
# Vmin = 0.95 p.u., cap_limit = 0.05 p.u.,  allow BESS islanding with SoC = 1.0 (100% of energy capacity available)
BESS_buses[20]["SoC"] = 1.0
run_and_plot_contingency(Example_20_Bus_Test_system, contingency_id, Vmin=0.95, cap_limit=0.05, plot=True, BESS_buses=BESS_buses, enable_bess_islanding=True)