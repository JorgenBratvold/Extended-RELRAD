import math

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
