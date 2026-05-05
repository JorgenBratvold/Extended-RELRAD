from Extended_RELRAD.src.load_flow import lin_dist_flow
from Extended_RELRAD.src.utils import find_reachable_buses

def branch_and_bound(
    network,
    slack_bus,
    children_mapping,
    parent_mapping,
    reachable_buses,
    Vmin=None,
    Vpre=None,
    capacity=None,
    faulted_buses=None,
):
    """
    Performs a branch-and-bound algorithm to find the optimal set of switch operations that 
    minimizes load shedding while ensuring system feasibility of capacity and voltage constraints.

    args:
        network: The power system network data structure containing buses, lines, edge_lookup, and upstream_lookup.
        slack_bus: The ID of the slack bus to optimize from.
        children_mapping: A dictionary mapping each bus to its child buses in the network topology.
        parent_mapping: A dictionary mapping each bus to its parent bus in the network topology.
        reachable_buses: A set of bus IDs that are reachable from the slack bus.
        Vmin: Minimum voltage limit for the optimization (optional).
        Vpre: A mapping of bus IDs to their pre-fault voltage magnitudes (optional).
        capacity: Capacity limit for the optimization (optional).
        faulted_buses: An optional set of bus IDs that are considered faulted and should not be energized. must be included to handle cases with fault on the same line a CB.
    
    returns:
        energized_buses: A set of bus IDs that are energized after applying the optimal switching actions.
        shed_nodes: A set of bus IDs that are shed (not energized) after applying the optimal switching actions.
    """

    lines = network["lines"]
    buses = network["buses"]
    edge_lookup = network["edge_lookup"]

    best_shed = float("inf")
    best_lines_snapshot = None

    def capacity_ok(children_mapping):
        """
        Checks if the total active power load in a specified subtree of the network
        is within the given capacity limit.
        
        args:
            children_mapping: A dictionary mapping each bus to its child buses in the network topology.
        
        returns:
            True if the total load in the subtree rooted at the slack bus is within the capacity limit, False otherwise.
        """

        if capacity is None:
            return True

        def subtree_load(bus):
            """
            Recursively calculates the total active power load in the subtree rooted at the given bus.
            
            args:
                bus: The ID of the bus at which to start the recursive calculation.
            
            returns:
                The total active power load in the subtree rooted at bus.
            """

            P = buses[bus]["P"]
            for child in children_mapping[bus]:
                P += subtree_load(child)
            return P

        total_load = subtree_load(slack_bus)

        return total_load <= capacity

    def build_switching_candidates():
        """
        Builds the switching candidates for the branch-and-bound algorithm. 
        Each candidate corresponds to a bus that can be disconnected from its 
        parent bus by opening the disconnector on the line connecting them.

        args:
            None
        
        returns:
            A dictionary mapping each candidate bus ID to its corresponding subtree of load, shed cost, line ID, and action key for switching.
        """

        def subtree(bus):
            """
            Recursively finds all buses in the subtree rooted at the given bus.

            args:
                bus: The ID of the bus at which to start the recursive search.

            returns:
                A set of bus IDs that are in the subtree rooted at bus.
            """

            S = {bus}
            for child in children_mapping[bus]:
                S |= subtree(child)

            return S

        Candidates = {}

        for bus, parent_bus in parent_mapping.items():

            line_id = edge_lookup.get((parent_bus, bus))
            line_disconnector = lines[line_id]["disc"] if line_id else "N"

            if line_disconnector != "N":

                T = subtree(bus)

                Pc = sum(
                    buses[m]["P_load"] * buses[m].get("c4", 1) * network.get("Sbase", 1) * 1000 # P_load is in p.u. and c4 is in nok/kWh, this converts to nok/h
                    for m in T)

                line = lines[line_id]

                if line["disc"] == "U":
                    action_key = "open_up"

                elif line["disc"] == "D":
                    action_key = "open_down"

                else:
                    action_key = ("open_up" if bus == line["up"] else "open_down")

                Candidates[bus] = {"subtree": T, "shed_cost": Pc, "line_id": line_id, "action_key": action_key}

        sorted(Candidates, key=lambda x: Candidates[x]["shed_cost"], reverse=True)

        return Candidates

    candidates = build_switching_candidates()

    def apply_candidate_switching(selected_candidate_ids):
        """
        Applies temporary switching actions.

        For each selected candidate, the related line is changed by setting its
        switch-action key to True. The old value is saved so the change can be
        undone later.
        """

        changes = []

        for candidate_id in selected_candidate_ids:
            candidate = candidates[candidate_id]

            line_id = candidate["line_id"]
            action_key = candidate["action_key"]

            line = lines[line_id]
            old_value = line.get(action_key)

            changes.append((line, action_key, old_value))

            line[action_key] = True

        return changes

    def undo_candidate_switching(changes):
        """
        Undoes temporary switching actions.

        The function restores each changed line to the value it had before
        apply_candidate_switching() was called.
        """

        for line, action_key, old_value in reversed(changes):

            if old_value is None:
                line.pop(action_key, None)
            else:
                line[action_key] = old_value
                
    def feasibility_check(selected_candidate_ids):
        """
        Checks the feasibility of a given set of switching candidates by applying the corresponding
        switching actions and evaluating the resulting system state against voltage and capacity constraints.
        
        args:
            selected_candidate_ids: A set of candidate bus IDs for which the corresponding switching actions should be applied for the feasibility check.
        
        returns:
            feasible: A boolean indicating whether the system state resulting from applying the selected switching actions is feasible according to the defined constraints.
            snapshot: A snapshot of the line states after feasibility check, which can be set as new optimal line states if the solution is found to be feasible and better than the current best solution.
        """

        changes = apply_candidate_switching(selected_candidate_ids)

        _, _, children_mapping = find_reachable_buses(slack_bus, buses,
            lines, faulted_buses=faulted_buses)
        
        feasible = True

        if feasible and capacity is not None:
            if not capacity_ok(children_mapping):
                feasible = False

        if feasible and Vmin is not None:
            V, _, _ = lin_dist_flow(
                network,
                slack_bus,
                children_mapping,
                Vpre=Vpre)
            
            if min(V.values()) < Vmin:
                feasible = False

        snapshot = None

        if feasible:
            snapshot = {
                line_id: dict(lines[line_id])
                for line_id in lines}

        undo_candidate_switching(changes)

        return feasible, snapshot

    all_candidates = set(candidates.keys())
    
    feasible, _ = feasibility_check(all_candidates)
    
    if not feasible:
        final_energized = set()
        shed_nodes = set(reachable_buses)
        return final_energized, shed_nodes
    
    def b_and_b_search(remaining, selected, shedset):
        """
        Recursive branch-and-bound search function that explores different combinations of switching candidates to
        find the optimal solution that minimizes load shedding while ensuring system feasibility.

        args:
            remaining: A list of candidate bus IDs that have not yet been selected for switching.
            selected: A set of candidate bus IDs that have been selected for switching in the current branch of the search.
            shedset: A set of bus IDs that are currently considered shed (not energized) based on the selected switching candidates.

        returns:
            None (the function updates the nonlocal variables best_shed and best_lines_snapshot with the best solution found during the search)
        """

        nonlocal best_shed
        nonlocal best_lines_snapshot

        current_shed = sum(
            candidates[g]["shed_cost"]
            for g in selected)

        if current_shed >= best_shed:
            return

        feasible, _ = feasibility_check(selected | set(remaining))

        if not feasible:
            return

        feasible, snapshot = feasibility_check(selected)

        if feasible:
            best_shed = current_shed
            best_lines_snapshot = snapshot
            return

        for i, g in enumerate(remaining):

            if candidates[g]["subtree"].issubset(shedset):
                continue

            b_and_b_search(remaining[i + 1 :], selected | {g},
                shedset | candidates[g]["subtree"])

    b_and_b_search(list(candidates.keys()), set(), set())

    if best_lines_snapshot:

        for line_id in lines:

            lines[line_id].clear()
            lines[line_id].update(
                best_lines_snapshot[line_id])

    energized_buses, parent_mapping, children_mapping = find_reachable_buses(
        slack_bus, buses, lines, faulted_buses=faulted_buses)

    shed_nodes = set(reachable_buses) - set(energized_buses)

    return energized_buses, shed_nodes
