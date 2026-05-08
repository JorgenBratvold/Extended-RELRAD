'''
Copyright (C) 2026 Jørgen Bratvold.

Part of a GPLv3-licensed thesis implementation derived in part from
RELRAD-software by Sondre Modalsli Aaberg.

Licensed under the GNU General Public License v3.0 or later.
See LICENSE for details.
'''

# IEEE 123-bus system with single reserve connection case study (only for testing purposes)
IEEE_123_Bus_system = {
    "path": "Extended_RELRAD/compatible_systems/IEEE_123Bus.xlsx",

    # First bus is the primary substation bus. These slack buses are used in single contingency plotting.
    "default_slack_buses": [1, 115],

    # Base apparent power [MVA]
    "Sbase": 10,
}

# IEEE 123-bus single-RC cases
IEEE_123_Bus_single_RC_cases = [
    # name              slack_buses  Vmin [p.u.]     cap_limit [p.u.]  bess_buses    enable_bess_islanding
    ("Base-RC90",       [1, 115],    0.00,           1000,             {},           False),
]