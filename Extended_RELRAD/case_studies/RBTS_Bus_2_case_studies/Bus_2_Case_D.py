# RBTS Bus 2 case D system case study
Bus_2_Case_D_system = {
    "path": "Extended_RELRAD/compatible_systems/RBTS_Bus_2/Bus_2_Case_D.xlsx",

    # First bus is the primary substation bus. These buses are used in single contingency plotting.
    "default_slack_buses": [23, 28, 30, 34, 38],

    # Base apparent power [MVA]
    "Sbase": 10,
}

# RBTS Bus 2 – case D
Bus_2_Case_D_cases = [
    # name         slack_buses              Vmin [p.u.]     cap_limit [p.u.]  bess_buses    enable_bess_islanding
    ("Base-D",     [23, 28, 30, 34, 38],    None,           None,             {},           False),
    ("Cap2.5-D",   [23, 28, 30, 34, 38],    None,           0.25,             {},           False),
    ("Cap2.0-D",   [23, 28, 30, 34, 38],    None,           0.20,             {},           False),
    ("Cap1.5-D",   [23, 28, 30, 34, 38],    None,           0.15,             {},           False),
    ("Cap1.0-D",   [23, 28, 30, 34, 38],    None,           0.10,             {},           False),
]