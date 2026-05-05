
def find_reachable_buses(slack_bus, buses, lines, faulted_buses=None):
    """
    Perform a depth-first search (DFS) to find all buses reachable from the given slack bus,
    while respecting the status of line disconnectors and optionally excluding faulted buses.
    
    args:
        slack_bus: ID of the slack bus to start the search from
        buses: dictionary of bus data
        lines: dictionary of line data
        faulted_buses: optional set of bus IDs that are considered faulted 
                        and should be excluded from the search
    
    returns:
        reachable_buses: A set of bus IDs that are reachable from the slack bus.
        parent_mapping: A dictionary mapping each bus to its parent bus.
        children_mapping: A dictionary mapping each bus to its child buses.

    """

    reachable_buses = set()
    parent_mapping = {}
    children_mapping = {b: set() for b in buses}

    def dfs(bus, parent_bus=None):

        if bus in reachable_buses or (faulted_buses is not None and bus in faulted_buses):
            return

        reachable_buses.add(bus)

        if parent_bus is not None:
            parent_mapping[bus] = parent_bus
            children_mapping[parent_bus].add(bus)
        for line_id in buses[bus]["connected_lines"]:
            line = lines[line_id]

            line_disconnector = line["disc"]
            if (
                (line_disconnector == "U" and line.get("open_up", False)) or
                (line_disconnector == "D" and line.get("open_down", False)) or
                (line_disconnector == "B" and (
                    line.get("open_up", False) or
                    line.get("open_down", False)
                ))
            ):
                continue

            nxt_bus = line["down"] if line["up"] == bus else line["up"]

            dfs(nxt_bus, bus)

    dfs(slack_bus, None)

    return reachable_buses, parent_mapping, children_mapping

def compute_switch_time(energized_buses, lines):
    """
    Computes the maximum switch time among all disconnectors that are open and 
    connected to a set of energized buses.

    args:
        energized_buses: set of bus IDs that are energized
        lines: dictionary of line data

    returns:
        The maximum switch time among all open disconnectors connected to the energized buses.
    """

    if not energized_buses:
        return 0.0

    Tsw = 0.0

    for line in lines.values():

        line_disconnector = line["disc"]

        is_open = (
            (line_disconnector == "U" and line.get("open_up", False)) or
            (line_disconnector == "D" and line.get("open_down", False)) or
            (line_disconnector == "B" and (
                line.get("open_up", False) or
                line.get("open_down", False)
            )))
        
        if not is_open:
            continue

        if line["up"] in energized_buses or line["down"] in energized_buses:
            Tsw = max(Tsw, float(line["switch_time"]))

    return Tsw