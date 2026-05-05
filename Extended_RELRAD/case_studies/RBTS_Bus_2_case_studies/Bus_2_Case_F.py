# RBTS Bus 2 case F system case study
Bus_2_Case_F_system = {
    "path": "Extended_RELRAD/compatible_systems/RBTS_Bus_2/Bus_2_Case_F.xlsx",

    # First bus is the primary substation bus. These buses are used in single contingency plotting.
    "default_slack_buses": [23],

    # Base apparent power [MVA]
    "Sbase": 10,
}

# RBTS Bus 2 – case F
Bus_2_Case_F_cases = [
    # name         slack_buses      Vmin [p.u.]     cap_limit [p.u.]    bess_buses    enable_bess_islanding
    ("Base-F",     [23],            None,           None,               {},           False),
]