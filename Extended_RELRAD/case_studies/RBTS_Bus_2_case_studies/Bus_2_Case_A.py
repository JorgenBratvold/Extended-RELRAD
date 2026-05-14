'''
Copyright (C) 2026 Jørgen Bratvold.

Part of a GPLv3-licensed thesis implementation derived in part from
RELRAD-software by Sondre Modalsli Aaberg.

Licensed under the GNU General Public License v3.0 or later.
See LICENSE for details.
'''

# RBTS Bus 2 case A system case study
Bus_2_Case_A_system = {
    "path": "Extended_RELRAD/compatible_systems/RBTS_Bus_2/Bus_2_Case_A.xlsx",

    # First bus is the primary substation bus. These slack buses are used in single contingency plotting.
    "default_slack_buses": [23, 28, 30, 34, 38],

    # Base apparent power [MVA]
    "Sbase": 10,
}

# RBTS Bus 2 – case A
Bus_2_Case_A_cases = [
    # name         slack_buses             Vmin [p.u.]     cap_limit [p.u.]  bess_buses    enable_bess_islanding
    ("Base-A",     [23, 28, 30, 34, 38],   None,           None,             {},           False),
    ("Cap2.5-A",   [23, 28, 30, 34, 38],   None,           0.25,             {},           False),
    ("Cap2.0-A",   [23, 28, 30, 34, 38],   None,           0.20,             {},           False),
    ("Cap1.5-A",   [23, 28, 30, 34, 38],   None,           0.15,             {},           False),
    ("Cap1.0-A",   [23, 28, 30, 34, 38],   None,           0.10,             {},           False),
]