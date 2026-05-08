import numpy as np

from Extended_RELRAD.src.utils import find_reachable_buses
from Extended_RELRAD.src.system_setup import build_network
from Extended_RELRAD.src.load_flow import lin_dist_flow, DALF

'''
Copyright (C) 2026 Jørgen Bratvold.

Part of a GPLv3-licensed thesis implementation derived in part from
RELRAD-software by Sondre Modalsli Aaberg.

Licensed under the GNU General Public License v3.0 or later.
See LICENSE for details.
'''

def study_scaling_table(EXCEL_PATH):
    """
    Compares the voltage results of the LinDistFlow solver and the DALF solver
    across a range of load scaling factors, and prints a table of the worst-case voltage error for each scale.
    """

    root = 0
    scales = np.linspace(0.5, 3.0, 6)

    print("\nVoltage comparison: DALF vs BFS")
    print("-" * 78)
    print(f"{'Scale':>6} {'Bus':>6} {'V_DALF (pu)':>12} {'V_BFS (pu)':>12} {'Error (%)':>12}")
    print("-" * 78)

    for s in scales:

        net = build_network(EXCEL_PATH)

        for b in net["buses"]:
            net["buses"][b]["P"] *= s
            net["buses"][b]["Q"] *= s

        _, _, children = find_reachable_buses(root, net["buses"], net["lines"])

        V_bfs, _, _ = lin_dist_flow(net, root, children)

        dalf = DALF()
        dalf.build_from_network(net, root, children)
        V_full = dalf.solve()

        V_dalf = {
            b: abs(V_full[dalf.bus_pos[b]])
            for b in net["buses"]
        }

        errors = {
            b: V_bfs.get(b, 1.0) - V_dalf.get(b, 1.0)
            for b in net["buses"]
        }

        worst_bus = max(errors, key=lambda b: abs(errors[b]))

        V_f = V_dalf[worst_bus]
        V_b = V_bfs[worst_bus]
        err_pct = 100 * (V_b - V_f) / V_f

        print(f"{s:6.2f} {worst_bus+1:6d} {V_f:12.5f} {V_b:12.5f} {err_pct:+12.2f}")

    print("-" * 78)

if __name__ == "__main__":
    study_scaling_table(EXCEL_PATH = "Extended_RELRAD/compatible_systems/CINELDI.xlsx")