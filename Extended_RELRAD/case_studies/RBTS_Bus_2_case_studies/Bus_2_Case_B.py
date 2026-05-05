# RBTS Bus 2 case B system case study
Bus_2_Case_B_system = {
    "path": "Extended_RELRAD/compatible_systems/RBTS_Bus_2/Bus_2_Case_B.xlsx",

    # First bus is the primary substation bus. These slack buses are used in single contingency plotting.
    "default_slack_buses": [23],

    # Base apparent power [MVA]
    "Sbase": 10,
}

# RBTS Bus 2 – case B
Bus_2_Case_B_cases = [
    # name         slack_buses      Vmin [p.u.]     cap_limit [p.u.]    bess_buses    enable_bess_islanding
    ("Base-B",     [23],            None,           None,               {},           False),
]