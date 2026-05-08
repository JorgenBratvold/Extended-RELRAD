
import copy

from Extended_RELRAD.src.utils import find_reachable_buses, compute_switch_time
from Extended_RELRAD.src.optimization import branch_and_bound

'''
Copyright (C) 2026 Jørgen Bratvold.

Part of a GPLv3-licensed thesis implementation derived in part from
RELRAD-software by Sondre Modalsli Aaberg.

Licensed under the GNU General Public License v3.0 or later.
See LICENSE for details.
'''

def get_available_bess_power(BESS_buses, ext_bus, repair_time):
    """
    Computes the available power from a BESS at a given bus, considering both the power capacity and the energy capacity over the repair time.

    args:
        BESS_buses: A dictionary mapping bus numbers to their BESS parameters (energy capacity, power capacity, state of charge, efficiency).
        ext_bus: The 1-indexed bus numbering for which to compute the available BESS power.
        repair_time: The expected repair time.

    returns:
        The available power from the BES at the specified bus
    """

    bess = BESS_buses[ext_bus]
    return min(
        bess["P"],
        bess["E"] * bess["eta"] * bess["SoC"] / repair_time)

def apply_bess_injection(
    buses_case,
    reachable_buses,
    BESS_buses,
    repair_time,
    exclude_bus=None):
    """
    Applies the BESS power injection to the reachable buses,
    excluding the specified bus that is a BESS units adopted as a slack bus.

    args:
        buses_case: A copy of the original bus data dictionary.
        reachable_buses: A list of bus numbers that are reachable from the BESS slack bus.
        BESS_buses: A dictionary mapping bus numbers to their BESS parameters (energy capacity, power capacity, state of charge, efficiency).
        repair_time: The expected repair time.
        exclude_bus: A bus number to exclude BESS power injection.

    returns:
        Updated buses_case with BESS power injection applied to the reachable buses, excluding the specified bus.
    """

    if not BESS_buses:
        return buses_case

    for bus in reachable_buses:
        if bus == exclude_bus:
            continue

        if (bus + 1) in BESS_buses:
            P_BESS = get_available_bess_power(BESS_buses, bus + 1, repair_time)
            buses_case[bus]["P"] -= P_BESS

    return buses_case

def apply_bess_islanding(
    BESS_buses,
    affected_buses,
    faulted_buses,
    total_energized_buses,
    total_shedded_buses,
    bus_owner_mapping,
    supply_type_mapping,
    switching_times_mapping,
    buses_base,
    line_copy,
    edge_lookup,
    repair_time,
    Vmin,
    V_pre_mapping):
    """
    Applies the BESS islanding by selecting candidate BESS buses as slack buses,
    computing the reachable buses, and performing branch and bound to determine the energized and shedded buses.

    args:
        BESS_buses: A dictionary mapping bus numbers to their BESS parameters (energy capacity, power capacity, state of charge, efficiency).
        affected_buses: A set of bus numbers that are affected by the fault.
        faulted_buses: A set of bus numbers that are faulted and cannot be energized.
        total_energized_buses: A set of bus numbers that are already energized by previous slack buses.
        total_shedded_buses: A set of bus numbers that are already shedded by previous slack buses.
        bus_owner_mapping: A dictionary mapping bus numbers to their respective slack bus owner.
        supply_type_mapping: A dictionary mapping bus numbers to their supply type (e.g., "main_slack", "bess_slack").
        switching_times_mapping: A dictionary mapping bus numbers to their switching times.
        buses_base: The original bus data dictionary before any modifications.
        line_copy: A copy of the original line data dictionary before any modifications.
        edge_lookup: A dictionary mapping bus pairs to their corresponding line indices.
        repair_time: The expected repair time.
        Vmin: The minimum voltage threshold for energizing buses.
        V_pre_mapping: A dictionary mapping bus numbers to their pre-fault voltage magnitudes.
    
    returns: 
        None 
        (Updated total_energized_buses, total_shedded_buses, bus_owner_mapping,
        supply_type_mapping, and switching_times_mapping after applying BESS islanding)
    """

    bess_internal_buses = {ext_bus - 1 for ext_bus in BESS_buses.keys()} # zero-indexed 

    candidate_bess_buses = [ # In isolated or shedded buses
        b for b in bess_internal_buses
        if b in affected_buses
        and b not in faulted_buses
        and b not in total_energized_buses]

    candidate_bess_buses = sorted(
        candidate_bess_buses,
        key=lambda bus: get_available_bess_power(BESS_buses, bus + 1, repair_time),
        reverse=True)

    for slack_bus_BESS in candidate_bess_buses:
        P_cap = get_available_bess_power(
            BESS_buses, slack_bus_BESS + 1, repair_time)

        buses_case = copy.deepcopy(buses_base)

        reachable_buses, parent_mapping, children_mapping = find_reachable_buses(
            slack_bus_BESS,
            buses_case,
            line_copy,
            faulted_buses=faulted_buses)

        # Speeds up by skipping optimization for slack buses that cannot energize any new buses beyond those already energized by previous slack buses. This can happen when the fault is close to the slack bus or when the network is heavily damaged.
        if not (set(reachable_buses) - set(total_energized_buses)):
            continue

        buses_case = apply_bess_injection(
            buses_case=buses_case,
            reachable_buses=reachable_buses,
            BESS_buses=BESS_buses,
            repair_time=repair_time,
            exclude_bus = slack_bus_BESS)

        energized_buses, shedded_buses = branch_and_bound(
            network={
                "buses": buses_case,
                "lines": line_copy,
                "edge_lookup": edge_lookup},
            slack_bus=slack_bus_BESS,
            children_mapping=children_mapping,
            parent_mapping=parent_mapping,
            reachable_buses=reachable_buses,
            Vmin=Vmin,
            Vpre=V_pre_mapping.get(slack_bus_BESS, 1.0),
            capacity=P_cap,
            faulted_buses=faulted_buses)

        total_energized_buses |= set(energized_buses)
        total_shedded_buses |= set(shedded_buses)
        total_shedded_buses -= set(energized_buses)

        switch_time = compute_switch_time(energized_buses, line_copy)

        bus_owner_mapping[slack_bus_BESS] = slack_bus_BESS
        supply_type_mapping[slack_bus_BESS] = "bess_slack"

        for b in energized_buses:
            switching_times_mapping[b] = switch_time
            bus_owner_mapping[b] = slack_bus_BESS
            supply_type_mapping[b] = "bess_slack"
