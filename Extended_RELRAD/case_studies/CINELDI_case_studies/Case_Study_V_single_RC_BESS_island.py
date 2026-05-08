'''
Copyright (C) 2026 Jørgen Bratvold.

Part of a GPLv3-licensed thesis implementation derived in part from
RELRAD-software by Sondre Modalsli Aaberg.

Licensed under the GNU General Public License v3.0 or later.
See LICENSE for details.
'''

# CINELDI system with islanded and grid-connected BESS case study
Case_Study_V_system = {
    "path": "Extended_RELRAD/compatible_systems/CINELDI.xlsx",

    # First bus is the primary substation bus. These slack buses are used in single contingency plotting.
    "default_slack_buses": [1, 62],

    # Base apparent power [MVA]
    "Sbase": 10,
}


# BESS units
BESS_all = {
    # bus    Energy capacity [p.u.]    Maximum power capacity [p.u.]    State of charge [-]    Efficiency [-]
    25:  {   "E": 0.2,                 "P": 0.05,                       "SoC": 0.5,            "eta": 0.94**2},
    90:  {   "E": 0.2,                 "P": 0.05,                       "SoC": 0.5,            "eta": 0.94**2},
    121: {   "E": 0.2,                 "P": 0.05,                       "SoC": 0.5,            "eta": 0.94**2},
}


# CINELDI single-RC BESS cases with and without BESS islanding contribution

Case_Study_V_cases = [
    # name                              slack_buses  Vmin [p.u.]     cap_limit [p.u.]  BESS units    allow_bess_islanding
    ("V095-Cap1-RC62",                  [1, 62],     0.95,           0.1,              {},           True),
    ("V095-Cap2-RC62",                  [1, 62],     0.95,           0.2,              {},           True),
    ("V095-Cap3-RC62",                  [1, 62],     0.95,           0.3,              {},           True),
    ("V095-Cap1-RC62-BESS-island",      [1, 62],     0.95,           0.1,              BESS_all,     True),
    ("V095-Cap2-RC62-BESS-island",      [1, 62],     0.95,           0.2,              BESS_all,     True),
    ("V095-Cap3-RC62-BESS-island",      [1, 62],     0.95,           0.3,              BESS_all,     True),
    ("V095-Cap1-RC62-BESS-grid",        [1, 62],     0.95,           0.1,              BESS_all,     False),
    ("V095-Cap2-RC62-BESS-grid",        [1, 62],     0.95,           0.2,              BESS_all,     False),
    ("V095-Cap3-RC62-BESS-grid",        [1, 62],     0.95,           0.3,              BESS_all,     False),
]
