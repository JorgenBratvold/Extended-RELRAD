import numpy as np

from NEW_CODE.RELRAD_v2 import build_network, Reachable, lindistflow

EXCEL_PATH = "NEW_CODE/new_systems/CINELDI.xlsx"


class DLF:

    def __init__(self):
        self.slack_voltage = 1.0 + 0j

    def build_from_network(self, network, root, children):

        buses = network["buses"]
        sections = network["sections"]
        edge_lookup = network["edge_lookup"]

        self.slack = root
        self.buses = sorted(buses.keys())
        self.non_slack = [b for b in self.buses if b != root]

        self.bus_pos = {b: i for i, b in enumerate(self.buses)}
        self.ns_pos = {b: i for i, b in enumerate(self.non_slack)}

        self.S_load = {
            b: buses[b]["P"] + 1j * buses[b]["Q"]
            for b in buses
        }

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

        self.DLF = self.BCBV @ self.BIBC
        self.build_A()


    def _build_BIBC(self):

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

            dV = self.DLF @ I_total
            V[ns_idx] = 1 + dV

            if np.max(np.abs(V - V_prev)) < tol:
                break

        return V

def study_scaling_table():

    root = 0
    scales = np.linspace(0.5, 3.0, 6)

    print("\nVoltage comparison: DLF vs BFS")
    print("-" * 78)
    print(f"{'Scale':>6} {'Bus':>6} {'V_DLF (pu)':>12} {'V_BFS (pu)':>12} {'Error (%)':>12}")
    print("-" * 78)

    for s in scales:

        net = build_network(EXCEL_PATH)

        # scale loads
        for b in net["buses"]:
            net["buses"][b]["P"] *= s
            net["buses"][b]["Q"] *= s

        _, _, children = Reachable(root, net["buses"], net["sections"])

        V_bfs, _, _ = lindistflow(net, root, children)

        dlf = DLF()
        dlf.build_from_network(net, root, children)
        V_full = dlf.solve()

        V_dlf = {
            b: abs(V_full[dlf.bus_pos[b]])
            for b in net["buses"]
        }

        errors = {
            b: V_bfs.get(b, 1.0) - V_dlf.get(b, 1.0)
            for b in net["buses"]
        }

        worst_bus = max(errors, key=lambda b: abs(errors[b]))

        V_f = V_dlf[worst_bus]
        V_b = V_bfs[worst_bus]
        err_pct = 100 * (V_b - V_f) / V_f

        print(f"{s:6.2f} {worst_bus+1:6d} {V_f:12.5f} {V_b:12.5f} {err_pct:+12.2f}")

    print("-" * 78)

if __name__ == "__main__":
    study_scaling_table()