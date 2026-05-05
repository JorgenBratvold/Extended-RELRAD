# RBTS Bus 4 case E system case study
Bus_4_Case_E_system = {
    "path": "Extended_RELRAD/compatible_systems/RBTS_Bus_4/Bus_4_Case_E.xlsx",

    # First bus is the primary substation bus. These slack buses are used in single contingency plotting.
    "default_slack_buses": [68, 43, 46, 51, 56, 59, 62, 67],
    # Base apparent power [MVA]
    "Sbase": 10,
}

# RBTS Bus 4 – case E
Bus_4_Case_E_cases = [
    # name         slack_buses                            Vmin [p.u.]     cap_limit [p.u.]  bess_buses    enable_bess_islanding
    ("Base-E",     [68, 43, 46, 51, 56, 59, 62, 67],      None,           None,             {},           False),
]