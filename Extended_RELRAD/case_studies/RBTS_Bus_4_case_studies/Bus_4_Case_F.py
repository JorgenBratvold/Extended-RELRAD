# RBTS Bus 4 case F system case study
Bus_4_Case_F_system = {
    "path": "Extended_RELRAD/compatible_systems/RBTS_Bus_4/Bus_4_Case_F.xlsx",

    # First bus is the primary substation bus. These slack buses are used in single contingency plotting.
    "default_slack_buses": [68],
    # Base apparent power [MVA]
    "Sbase": 10,
}

# RBTS Bus 4 – case F
Bus_4_Case_F_cases = [
    # name         slack_buses        Vmin [p.u.]     cap_limit [p.u.]  bess_buses    enable_bess_islanding
    ("Base-F",     [68],              None,           None,             {},           False),
]