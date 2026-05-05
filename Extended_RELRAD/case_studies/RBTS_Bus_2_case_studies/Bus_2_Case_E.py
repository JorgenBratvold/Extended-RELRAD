# RBTS Bus 2 case E system case study
Bus_2_Case_E_system = {
    "path": "Extended_RELRAD/compatible_systems/RBTS_Bus_2/Bus_2_Case_E.xlsx",

    # First bus is the primary substation bus. These slack buses are used in single contingency plotting.
    "default_slack_buses": [23, 28, 30, 34, 38],

    # Base apparent power [MVA]
    "Sbase": 10,
}

# RBTS Bus 2 – case E
Bus_2_Case_E_cases = [
    # name         slack_buses              Vmin [p.u.]     cap_limit [p.u.]    bess_buses    enable_bess_islanding
    ("Base-E",     [23, 28, 30, 34, 38],    None,           None,               {},           False),
]