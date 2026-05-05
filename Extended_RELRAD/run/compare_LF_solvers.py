import numpy as np

from Extended_RELRAD.src.utils import find_reachable_buses
from Extended_RELRAD.src.system_setup import build_network
from Extended_RELRAD.src.load_flow import lin_dist_flow

EXCEL_PATH = "Extended_RELRAD/compatible_systems/CINELDI.xlsx"

class DALF:
    """
    Direct Approach Load Flow solver using BIBC/BCBV matrices, and including shunt admittances.
    """

    def __init__(self):
        self.slack_voltage = 1.0 + 0j

    def build_from_network(self, network, root, children):

        buses = network["buses"]
        sections = network["lines"]
        edge_lookup = network["edge_lookup"]

        self.slack = root
        self.buses = sorted(buses.keys())
        self.non_slack = [b for b in self.buses if b != root]

        self.bus_pos = {b: i for i, b in enumerate(self.buses)}
        self.ns_pos = {b: i for i, b in enumerate(self.non_slack)}

        self.S_load = {
            b: buses[b]["P"] + 1j * buses[b]["Q"]
            for b in buses}

        self.lines = []

        def traverse(node):
            for c in children[node]:
                sid = edge_lookup[(node, c)]
                sec = sections[sid]

                self.lines.append({
                    "From": node,
                    "To": c,
                    "r_pu": sec["r"],
                    "x_pu": sec["x"],
                    "b_pu": sec.get("b", 0.0) 
                })

                traverse(c)

        traverse(root)

        self.ysh_half = np.array(
            [1j * ln["b_pu"] / 2 for ln in self.lines],
            dtype=complex
        )

        self._build_BIBC()
        self._build_BCBV()

        self.DALF = self.BCBV @ self.BIBC
        self.build_A()


    def _build_BIBC(self):
        """
        Builds the BIBC (Bus Injection to Branch Current) matrix based on the network topology.
        """

        m = len(self.lines)
        n = len(self.non_slack)

        BIBC = np.zeros((m, n))

        for br, ln in enumerate(self.lines):
            f = ln["From"]
            t = ln["To"]

            col_t = self.ns_pos[t]

            if f != self.slack:
                col_f = self.ns_pos[f]
                BIBC[:, col_t] = BIBC[:, col_f]

            BIBC[br, col_t] = 1.0

        self.BIBC = BIBC


    def _build_BCBV(self):
        """
        Builds the BCBV (Branch Current to Bus Voltage) matrix based on the network topology and line impedances.
    """

        n = len(self.non_slack)
        m = len(self.lines)

        BCBV = np.zeros((n, m), dtype=complex)

        for br, ln in enumerate(self.lines):
            f = ln["From"]
            t = ln["To"]

            z = ln["r_pu"] + 1j * ln["x_pu"]

            row_t = self.ns_pos[t]

            if f != self.slack:
                row_f = self.ns_pos[f]
                BCBV[row_t, :] = BCBV[row_f, :]

            BCBV[row_t, br] = z

        self.BCBV = BCBV


    def build_A(self):
        """
        Builds the A matrix for shunt admittance calculations, based on the network topology and line shunt admittances.
        """

        A = np.zeros((len(self.non_slack), len(self.lines)))

        for br, ln in enumerate(self.lines):
            f = ln["From"]
            t = ln["To"]

            if f != self.slack:
                A[self.ns_pos[f], br] = 1
            if t != self.slack:
                A[self.ns_pos[t], br] = 1

        self.A = A


    def solve(self, tol=1e-8, max_iter=100):

        V = np.ones(len(self.buses), dtype=complex)
        V[self.bus_pos[self.slack]] = self.slack_voltage

        ns_idx = [self.bus_pos[b] for b in self.non_slack]

        for _ in range(max_iter):

            V_prev = V.copy()

            I_load = np.array([
                -np.conj(self.S_load[b]) / np.conj(V[self.bus_pos[b]])
                for b in self.non_slack
            ])

            I_sh = V[ns_idx] * (self.A @ self.ysh_half)

            I_total = I_load - I_sh

            dV = self.DALF @ I_total
            V[ns_idx] = 1 + dV

            if np.max(np.abs(V - V_prev)) < tol:
                break

        return V

def study_scaling_table():
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
    study_scaling_table()