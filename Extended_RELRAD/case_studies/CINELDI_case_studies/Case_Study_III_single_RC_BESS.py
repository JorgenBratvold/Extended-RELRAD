# CINELDI system with single reserve connection and BESS unit case study
Case_Study_III_system = {
    "path": "Extended_RELRAD/compatible_systems/CINELDI.xlsx",

    # First bus is the primary substation bus. These slack buses are used in single contingency plotting.
    "default_slack_buses": [1, 62],

    # Base apparent power [MVA]
    "Sbase": 10,
}

# BESS unit
BESS_121 = {
    # bus    Energy capacity [p.u.]    Maximum power capacity [p.u.]    State of charge [-]    Efficiency [-]
    121: {   "E": 0.2,                 "P": 0.05,                       "SoC": 0.5,            "eta": 0.94**2},
}

# CINELDI single-RC BESS cases
Case_Study_III_cases = [
    # name                       slack_buses  Vmin [p.u.]     cap_limit [p.u.]  BESS units    allow_bess_islanding
    ("V095-Cap1-RC62",           [1, 62],     0.95,           0.1,              {},           False),
    ("V095-Cap2-RC62",           [1, 62],     0.95,           0.2,              {},           False),
    ("V095-Cap3-RC62",           [1, 62],     0.95,           0.3,              {},           False),
    ("V095-Cap1-RC62-BESS121",   [1, 62],     0.95,           0.1,              BESS_121,     False),
    ("V095-Cap2-RC62-BESS121",   [1, 62],     0.95,           0.2,              BESS_121,     False),
    ("V095-Cap3-RC62-BESS121",   [1, 62],     0.95,           0.3,              BESS_121,     False),
]

