import math
import numpy as np

'''
Copyright (C) 2026 Jørgen Bratvold.

Part of a GPLv3-licensed thesis implementation derived in part from
RELRAD-software by Sondre Modalsli Aaberg.

Licensed under the GNU General Public License v3.0 or later.
See LICENSE for details.
'''

def backward_sweep(bus, children_mapping, buses, P_flow_mapping, Q_flow_mapping):
    """
    Performs the backward sweep of the LinDistFlow power flow calculation.
    Starting from the leaf buses, it recursively calculates the active and
    reactive power flow from the parent bus to the current bus,
    and updates the power flow mappings accordingly.

    args:
        bus: the current bus ID for which to calculate the power flow
        children_mapping: a mapping of each bus to its child buses in the network
        buses: a dictionary containing data for each bus, including load and generation
        P_flow_mapping: a dictionary to store the calculated active power flow to each bus
        Q_flow_mapping: a dictionary to store the calculated reactive power flow to each bus

    returns:
        P_parent_to_bus: the active power flow from the parent bus to the current bus
        Q_parent_to_bus: the reactive power flow from the parent bus to the current bus
    """

    P_parent_to_bus = buses[bus]["P"]
    Q_parent_to_bus = buses[bus]["Q"]

    for child_bus in children_mapping[bus]:
        P_bus_to_children, Q_bus_to_children = backward_sweep(child_bus, children_mapping, buses, P_flow_mapping, Q_flow_mapping)
        P_parent_to_bus += P_bus_to_children
        Q_parent_to_bus += Q_bus_to_children

    P_flow_mapping[bus] = P_parent_to_bus
    Q_flow_mapping[bus] = Q_parent_to_bus

    return P_parent_to_bus, Q_parent_to_bus

def forward_sweep(bus, children_mapping, lines, edge_lookup, P_flow_mapping, Q_flow_mapping, V2_mapping):
    """
    Performs the forward sweep of the LinDistFlow power flow calculation.
    Starting from the slack bus, it recursively calculates the voltage drop across each line to the child buses,
    and updates the V2 mapping accordingly.

    args:
        bus: the current bus ID for which to calculate the voltage drop to its child buses
        children_mapping: a mapping of each bus to its child buses in the network
        lines: a dictionary containing data for each line, including resistance and reactance
        edge_lookup: a mapping of bus pairs to line IDs for quick access to line data
        P_flow_mapping: a dictionary containing the active power flow to each bus, calculated from the backward sweep
        Q_flow_mapping: a dictionary containing the reactive power flow to each bus, calculated from the backward sweep
        V2_mapping: a dictionary to store the calculated squared voltage magnitude at each bus, which will be updated during the forward sweep
    
    returns:
        None (the function updates the V2_mapping)
    """

    V2_bus = V2_mapping[bus]

    for child in children_mapping[bus]:
        line_id = edge_lookup[(bus, child)]
        line = lines[line_id]

        V2_drop = 2 * (line["r"] * P_flow_mapping[child] + line["x"] * Q_flow_mapping[child])
        V2_mapping[child] = max(V2_bus - V2_drop, 0.0)

        forward_sweep(
            child, children_mapping, lines,
            edge_lookup, P_flow_mapping, Q_flow_mapping, V2_mapping)

def lin_dist_flow(network, slack_bus, children_mapping, Vpre=None):
    """
    Performs the LinDistFlow power flow calculation for the given network, starting from the specified slack bus. 
    It first executes the backward sweep to calculate the power flow to each bus, 
    and then the forward sweep to calculate the voltage at each bus.

    args: 
        network: a dictionary representing the network, containing "buses", "lines", and "edge_lookup"
        slack_bus: the ID of the slack bus from which to start the power flow calculation
        children_mapping: a mapping of each bus to its child buses in the network 
        Vpre: an optional dictionary of pre-contingency voltage magnitudes at each bus
    
    returns:
        V_mapping: a dictionary mapping each bus ID to its calculated voltage magnitude after the LinDistFlow calculation
        P_flow_mapping: a dictionary mapping each bus ID to the active power flow to that bus
        Q_flow_mapping: a dictionary mapping each bus ID to the reactive power flow to that bus
    """

    P_flow_mapping = {}
    Q_flow_mapping = {}

    backward_sweep(slack_bus, children_mapping, network["buses"], P_flow_mapping, Q_flow_mapping)

    V2_mapping = {slack_bus: (Vpre**2 if Vpre is not None else 1.0)}

    forward_sweep( slack_bus, children_mapping, network["lines"], network["edge_lookup"], P_flow_mapping, Q_flow_mapping, V2_mapping)
    
    return {n: math.sqrt(v) for n, v in V2_mapping.items()}, P_flow_mapping, Q_flow_mapping

# Direct Approach Load Flow (DALF) solver was implemented during specialization project
# and is included here for comparison with the LinDistFlow solver. 
# It is not used in the main RELRAD algorithm, but can be used for benchmarking and validation purposes.

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
