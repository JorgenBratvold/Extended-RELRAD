'''
Copyright (C) 2026 Jørgen Bratvold.

Part of a GPLv3-licensed thesis implementation derived in part from
RELRAD-software by Sondre Modalsli Aaberg.

Licensed under the GNU General Public License v3.0 or later.
See LICENSE for details.
'''

# CINELDI system with multiple reserve connections case study
Case_Study_II_system = {
    "path": "Extended_RELRAD/compatible_systems/CINELDI.xlsx",

    # First bus is the primary substation bus. These slack buses are used in single contingency plotting.
    "default_slack_buses": [1, 36, 62, 88],

    # Base apparent power [MVA]
    "Sbase": 10,
}

# CINELDI multi-RC cases
Case_Study_II_cases = [
    # name                slack_buses          Vmin [p.u.]     cap_limit [p.u.]  bess_buses    enable_bess_islanding
    ("Base-All",          [1, 36, 62, 88],     None,           None,             {},           False),
    ("V095-Cap1-AllRC",   [1, 36, 62, 88],     0.95,           0.1,              {},           False),
    ("V095-Cap2-AllRC",   [1, 36, 62, 88],     0.95,           0.2,              {},           False),
    ("V090-Cap2-AllRC",   [1, 36, 62, 88],     0.90,           0.2,              {},           False),
]