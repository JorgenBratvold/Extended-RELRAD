
import copy

from Extended_RELRAD.src.BESS_model import get_available_bess_power, apply_bess_islanding, apply_bess_injection
from Extended_RELRAD.src.load_flow import lin_dist_flow 
from Extended_RELRAD.src.protection_and_isolation import trip_upstream_protection, find_affected_buses, isolate_and_find_faulted_buses, identify_unused_protection
from Extended_RELRAD.src.optimization import branch_and_bound 
from Extended_RELRAD.src.utils import find_reachable_buses, compute_switch_time 

'''
Copyright (C) 2026 Jørgen Bratvold.

Part of a GPLv3-licensed thesis implementation derived in part from
RELRAD-software by Sondre Modalsli Aaberg.

Licensed under the GNU General Public License v3.0 or later.
See LICENSE for details.
'''

# Main RELRAD functions

def run_single_contingency(
    line_id,
    network,
    slack_buses,
    Vmin,
    Sbase,
    cap_limit,
    V_pre_mapping,
    BESS_buses=None,
    build_results=False,
    enable_bess_islanding=False,
    objective="load_shed"):
    """
    Runs a single contingency defined by a fault on a specific line. The function performs the following steps:
    1. Simulates the fault on the specified line and identifies the affected buses.
    2. Determines the faulted buses and the buses that are isolated due to the fault.
    3. Reclose any unused protection devices that were tripped due to the fault.
    4. For each slack bus, finds the reachable buses and applies BESS injection if applicable.
    5. Runs the branch-and-bound optimization to determine which buses can be energized and which need to be shedded.
    6. Computes the switching times for the energized buses 
    7. If enabled, applies BESS islanding to further energize buses.
    8. Computes the ENS contribution for each bus based on the state after restoration; Faulted, Isolated, Energized or Shedded.
    9. If requested, builds a detailed contingency result with the final system state after restoration (for later plotting).
    
    args:
        line_id: The ID of the line on which the fault occurs.
        network: The power system network data structure containing buses, lines, edge_lookup, and upstream_lookup.
        slack_buses: List of IDs of the slack buses in the system.
        Vmin: Minimum voltage limit of the bus voltage magnitudes.
        Sbase: Base apparent power for per-unit calculations.
        cap_limit: Capacity limit of the reserve connections.
        V_pre_mapping: A mapping of bus IDs to their pre-fault voltage magnitudes
        BESS_buses: Optional dictionary of BESS bus IDs and their parameters for injection and islanding.
        build_results: Whether to build a detailed contingency result for plotting (default: False)
        enable_bess_islanding: Whether to enable BESS islanding in the restoration process (default: False)
        objective: The objective function to optimize in the branch-and-bound ("load_shed" or "cost", default: "load_shed")

    returns: 
        ENS_contingency: A dictionary mapping each bus ID to its ENS contribution for this contingency.
        ENS_breakdown: A dictionary with breakdown of ENS contributions by category (fault, isolated, switching, shed) for each bus for this contingency.
        contingency_result: A detailed dictionary containing the final system state after restoration for this contingency, including line statuses, voltages, 
                            power flows, energized and shedded buses, bus ownership, supply types, and ENS breakdown. 
                            This is used for later plotting and analysis.
    """

    buses = network["buses"]
    lines = network["lines"]
    edge_lookup = network["edge_lookup"]

    line_copy = copy.deepcopy(lines)

    for line in line_copy.values(): 
        line["fault"] = False
        line.pop("open_up", None)
        line.pop("open_down", None)

    line_copy[line_id]["fault"] = True

    failure_rate = line_copy[line_id]["lambda"]
    repair_time = line_copy[line_id]["repair_time"]

    protection_id = trip_upstream_protection(line_id, line_copy, network["upstream_lookup"])
    affected_buses = find_affected_buses(protection_id, line_copy, buses)
    faulted_buses = isolate_and_find_faulted_buses(line_id, line_copy, buses)
    identify_unused_protection(protection_id, line_copy, faulted_buses)

    total_energized_buses = set()
    total_shedded_buses = set()
    switching_times_mapping = {}
    bus_owner_mapping = {}
    supply_type_mapping = {} 

    buses_base = copy.deepcopy(buses)

    for slack_bus in slack_buses:
        buses_case = copy.deepcopy(buses_base)

        reachable_buses, parent_mapping, children_mapping = find_reachable_buses(slack_bus, 
        buses_case, line_copy, faulted_buses=faulted_buses)

        # Speeds up by skipping optimization for slack buses that cannot energize any new buses beyond those already energized by previous slack buses. This can happen when the fault is close to the slack bus or when the network is heavily damaged.
        if not (set(reachable_buses) - set(total_energized_buses)):
            continue 

        buses_case = apply_bess_injection(buses_case=buses_case, reachable_buses=reachable_buses, 
                                                   BESS_buses=BESS_buses, repair_time=repair_time)

        P_cap = 1e8 if slack_bus == slack_buses[0] else cap_limit
        
        energized_buses, shedded_buses = branch_and_bound(
            network= { "buses": buses_case, "lines": line_copy, "edge_lookup": edge_lookup },
            slack_bus=slack_bus,
            children_mapping=children_mapping,
            parent_mapping=parent_mapping,
            reachable_buses=reachable_buses,
            Vmin=Vmin,
            Vpre=V_pre_mapping.get(slack_bus, 1.0),
            capacity=P_cap,
            faulted_buses=faulted_buses,
            objective=objective)

        total_energized_buses |= set(energized_buses)
        total_shedded_buses |= set(shedded_buses)
        total_shedded_buses -= set(energized_buses)

        switch_time = compute_switch_time(energized_buses, line_copy)

        bus_owner_mapping[slack_bus] = slack_bus
        supply_type_mapping[slack_bus] = "grid_slack"

        for b in energized_buses:
            switching_times_mapping[b] = switch_time
            bus_owner_mapping[b] = slack_bus
            supply_type_mapping[b] = "grid_slack"

    if enable_bess_islanding and BESS_buses:
        apply_bess_islanding(
            BESS_buses=BESS_buses,
            affected_buses=affected_buses,
            faulted_buses=faulted_buses,
            total_energized_buses=total_energized_buses,
            total_shedded_buses=total_shedded_buses,
            bus_owner_mapping=bus_owner_mapping,
            supply_type_mapping=supply_type_mapping,
            switching_times_mapping=switching_times_mapping,
            buses_base=buses_base,
            line_copy=line_copy,
            edge_lookup=edge_lookup,
            repair_time=repair_time,
            Vmin=Vmin,
            V_pre_mapping=V_pre_mapping,
            objective=objective)

    isolated_buses = (
        set(affected_buses)
        - set(faulted_buses)
        - set(total_energized_buses)
        - set(total_shedded_buses) )

    ENS_contingency = {bus: 0.0 for bus in buses}

    ENS_breakdown = {
        "fault": {bus: 0.0 for bus in buses},
        "isolated": {bus: 0.0 for bus in buses},
        "switching": {bus: 0.0 for bus in buses},
        "shed": {bus: 0.0 for bus in buses}}

    for bus in affected_buses:
        P_load = max(buses[bus]["P"], 0.0) * Sbase
        if P_load <= 0: # skip if no load
            continue

        if bus in faulted_buses:
            ENS_bus = failure_rate * repair_time * P_load # MWh/yr
            ENS_breakdown["fault"][bus] += ENS_bus 

        elif bus in total_energized_buses:
            ENS_bus = failure_rate * switching_times_mapping.get(bus, 0.0) * P_load
            ENS_breakdown["switching"][bus] += ENS_bus

        elif bus in total_shedded_buses:
            ENS_bus = failure_rate * repair_time * P_load 
            ENS_breakdown["shed"][bus] += ENS_bus

        elif bus in isolated_buses:
            ENS_bus = failure_rate * repair_time * P_load
            ENS_breakdown["isolated"][bus] += ENS_bus

        else:
            ENS_bus = 0.0

        ENS_contingency[bus] += ENS_bus

    contingency_result = None
    if build_results:
        buses_final = copy.deepcopy(buses)

        V_mapping_after = {}
        P_flow_mapping_after = {}
        Q_flow_mapping_after = {}
        parent_mapping_after = {}
        P_BESS_mapping = {}

        all_supply_buses = set(bus_owner_mapping.values())

        if BESS_buses:
            for bus in total_energized_buses:
                if (bus + 1) not in BESS_buses:
                    continue

                if supply_type_mapping.get(bus) == "bess_slack":
                    continue

                P_BESS = get_available_bess_power(BESS_buses, bus+1, repair_time)
                buses_final[bus]["P"] -= P_BESS
                P_BESS_mapping[bus] = P_BESS

        for supply_bus in all_supply_buses:
            reachable_buses, parent_mapping, children_mapping = find_reachable_buses(
                supply_bus,
                buses_final,
                line_copy,
                faulted_buses=faulted_buses)

            owned_buses = {
                b for b in reachable_buses
                if b == supply_bus or bus_owner_mapping.get(b) == supply_bus}

            if not owned_buses:
                continue

            filtered_children_mapping = {
                b: [c for c in children_mapping.get(b, []) if c in owned_buses]
                for b in owned_buses}

            filtered_parent_mapping = {
                b: p for b, p in parent_mapping.items()
                if b in owned_buses and p in owned_buses}

            V_mapping, P_flow_mapping, Q_flow_mapping = lin_dist_flow(
                {"buses": buses_final, "lines": line_copy, "edge_lookup": edge_lookup},
                supply_bus,
                filtered_children_mapping,
                Vpre=V_pre_mapping.get(supply_bus, 1.0))

            for b in owned_buses:
                if b in V_mapping:
                    V_mapping_after[b] = V_mapping[b]

            parent_mapping_after.update(filtered_parent_mapping)

            for key, val in P_flow_mapping.items():
                if isinstance(key, tuple) and len(key) == 2:
                    i, j = key
                    if i in owned_buses and j in owned_buses:
                        P_flow_mapping_after[key] = val
                elif key in owned_buses:
                    P_flow_mapping_after[key] = val
                elif key in line_copy:
                    line = line_copy[key]
                    i = line.get("from_bus", line.get("up"))
                    j = line.get("to_bus", line.get("down"))
                    if i in owned_buses and j in owned_buses:
                        P_flow_mapping_after[key] = val

            for key, val in Q_flow_mapping.items():
                if isinstance(key, tuple) and len(key) == 2:
                    i, j = key
                    if i in owned_buses and j in owned_buses:
                        Q_flow_mapping_after[key] = val
                elif key in owned_buses:
                    Q_flow_mapping_after[key] = val
                elif key in line_copy:
                    line = line_copy[key]
                    i = line.get("from_bus", line.get("up"))
                    j = line.get("to_bus", line.get("down"))
                    if i in owned_buses and j in owned_buses:
                        Q_flow_mapping_after[key] = val

        contingency_result = {
            "lines": line_copy,
            "voltages": V_mapping_after,
            "Pflows": P_flow_mapping_after,
            "Qflows": Q_flow_mapping_after,
            "energized_buses": total_energized_buses,
            "shed_nodes": total_shedded_buses,
            "switching_owner": bus_owner_mapping,
            "slack_buses": slack_buses,
            "BESS_buses": BESS_buses or {},
            "BESS_power": P_BESS_mapping or {},
            "faulted_buses": faulted_buses,
            "parent": parent_mapping_after,
            "ENS_contingency": copy.deepcopy(ENS_contingency),
            "ENS_breakdown": copy.deepcopy(ENS_breakdown),
            "affected_buses": set(affected_buses),
            "isolated_buses": set(isolated_buses),
            "supply_type_mapping": copy.deepcopy(supply_type_mapping)}

    return ENS_contingency, ENS_breakdown, contingency_result

def run_RELRAD(network, 
               slack_buses, 
               Vmin, 
               Sbase, 
               cap_limit, 
               BESS_buses=None, 
               enable_bess_islanding=False,
               objective="load_shed"):
    """
    Runs the RELRAD analysis for all single line contingencies in the network. 
    For each line contingency, it calls the run_single_contingency function to simulate the fault, 
    perform restoration, and compute ENS contributions. It aggregates the total ENS contributions and breakdown by category across all contingencies. Optionally, it can also build detailed contingency results for each line for later plotting and analysis.  

    args:
        network: The power system network data structure containing buses, lines, edge_lookup, and upstream_lookup.
        slack_buses: List of IDs of the slack buses in the system. First element is considered as the primary substation. 
        Vmin: Minimum voltage limit of the bus voltage magnitudes.
        Sbase: Base apparent power for the system.
        cap_limit: Capacity limit of reserve connections.
        BESS_buses: Optional dictionary of BESS bus IDs and their parameters for injection and islanding.
        enable_bess_islanding: Flag to enable/disable BESS islanding functionality.
        objective: The objective function to optimize in the branch-and-bound ("load_shed" or "cost", default: "load_shed")

    returns:
        ENS_total_LP: A dictionary mapping each bus ID to its total ENS contribution across all contingencies.
        ENS_breakdown_total: A dictionary with breakdown of total ENS contributions by category (fault, isolated, switching, shed) for each bus across all contingencies.
    """

    buses = network["buses"]
    slack_buses = [slack - 1 for slack in slack_buses]
    BESS_buses = BESS_buses or {}

    # Pre-fault voltage mapping for all buses based on the primary slack bus
    _, _, children_mapping = find_reachable_buses(slack_buses[0], buses, network["lines"], faulted_buses=None)
    V_pre_mapping, _, _ = lin_dist_flow(network, slack_buses[0], children_mapping)

    ENS_total_LP = {bus: 0.0 for bus in buses}
    ENS_breakdown_total = {
        "fault": {bus: 0.0 for bus in buses},
        "isolated": {bus: 0.0 for bus in buses},
        "switching": {bus: 0.0 for bus in buses},
        "shed": {bus: 0.0 for bus in buses} }
    
    RELRAD_results = {} 

    for line_id in network["lines"]:

        ENS_contingency, ENS_breakdown, _ = run_single_contingency(
            line_id=line_id, 
            network=network, 
            slack_buses=slack_buses, 
            Vmin=Vmin,
            Sbase=Sbase, 
            cap_limit=cap_limit, 
            V_pre_mapping=V_pre_mapping, 
            BESS_buses=BESS_buses,
            build_results=False,
            enable_bess_islanding=enable_bess_islanding,
            objective=objective)

    
        for bus, ENS_bus in ENS_contingency.items():
            ENS_total_LP[bus] += ENS_bus

        for category in ENS_breakdown_total:
            for bus, val in ENS_breakdown[category].items():
                ENS_breakdown_total[category][bus] += val

        RELRAD_results[line_id] = {
            "ENS_contingency": ENS_contingency,
            "ENS_breakdown": ENS_breakdown}

    return ENS_total_LP, ENS_breakdown_total, RELRAD_results

