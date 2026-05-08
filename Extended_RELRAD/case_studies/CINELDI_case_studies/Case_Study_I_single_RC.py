'''
Copyright (C) 2026 Jørgen Bratvold.

Part of a GPLv3-licensed thesis implementation derived in part from
RELRAD-software by Sondre Modalsli Aaberg.

Licensed under the GNU General Public License v3.0 or later.
See LICENSE for details.
'''

# CINELDI system with single reserve connection case study
Case_Study_I_system = {
    "path": "Extended_RELRAD/compatible_systems/CINELDI.xlsx",

    # First bus is the primary substation bus. These slack buses are used in single contingency plotting.
    "default_slack_buses": [1, 62],

    # Base apparent power [MVA]
    "Sbase": 10,
}

# CINELDI single-RC cases 
Case_Study_I_cases = [
    # name              slack_buses  Vmin [p.u.]     cap_limit [p.u.]  bess_buses    enable_bess_islanding
    ("Base-RC36",       [1, 36],     None,           None,             {},           False),
    ("Base-RC62",       [1, 62],     None,           None,             {},           False),
    ("Base-RC88",       [1, 88],     None,           None,             {},           False),

    ("V095-Cap1-RC36",  [1, 36],     0.95,           0.1,              {},           False),
    ("V095-Cap1-RC62",  [1, 62],     0.95,           0.1,              {},           False),
    ("V095-Cap1-RC88",  [1, 88],     0.95,           0.1,              {},           False),

    ("V095-Cap2-RC36",  [1, 36],     0.95,           0.2,              {},           False),
    ("V095-Cap2-RC62",  [1, 62],     0.95,           0.2,              {},           False),
    ("V095-Cap2-RC88",  [1, 88],     0.95,           0.2,              {},           False),

    ("V090-Cap2-RC36",  [1, 36],     0.90,           0.2,              {},           False),
    ("V090-Cap2-RC62",  [1, 62],     0.90,           0.2,              {},           False),
    ("V090-Cap2-RC88",  [1, 88],     0.90,           0.2,              {},           False),
]

