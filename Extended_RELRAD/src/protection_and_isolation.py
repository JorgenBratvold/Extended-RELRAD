'''
Adapted from RELRAD-software by Sondre Modalsli Aaberg.
Original copyright (C) 2025 Sondre Modalsli Aaberg.

Modifications copyright (C) 2026 Jørgen Bratvold.

Licensed under the GNU General Public License v3.0 or later.
See LICENSE for details.
'''


def trip_upstream_protection(faulted_line_id, lines, upstream_lookup):
    """
    Trips the nearest upstream protection device for a given faulted line. 
    
    args:
        faulted_line_id: ID of the line where the fault occurred
        lines: dictionary of line data
        upstream_lookup: dictionary mapping each bus to the line ID of the line connecting it to its parent bus (if any)

    returns:
        The ID of the tripped protection line, or None if no protection was tripped.
    """

    current_line_id = faulted_line_id

    while current_line_id is not None:

        line = lines[current_line_id]
        line_breaker = line.get("breaker", "N")

        if line_breaker in ("U", "D", "B"):

            switching_actions = {
                "U": ("open_up",),
                "D": ("open_down",),
                "B": ("open_up", "open_down"),
            }

            for key in switching_actions[line_breaker]:
                line[key] = True

            return current_line_id

        current_line_id = upstream_lookup.get(line["up"])

    return None

def find_affected_buses(protection_line_id, lines, buses):
    """
    Finds all buses that are affected by the tripping of a protection device on a given line.
    
    args:
        protection_line_id: ID of the line where the protection device is tripped
        lines: dictionary of line data
        buses: dictionary of bus data

    returns:
        A set of bus IDs that are affected by the tripping of the protection device.
    """

    if protection_line_id is None:
        return set(buses)

    line = lines[protection_line_id]
    line_breaker = line.get("breaker", "N")

    if line_breaker == "D":
        start_bus = line["up"]
    elif line_breaker in ("U", "B"):
        start_bus = line["down"]
    else:
        return set(buses)

    affected_buses = set()

    def dfs(bus):
        if bus in affected_buses:
            return
        affected_buses.add(bus)

        for line_id in buses[bus]["connected_lines"]:
            line = lines[line_id]

            if (
                (line.get("breaker") == "U" and line.get("open_up", False)) or
                (line.get("breaker") == "D" and line.get("open_down", False)) or
                (line.get("breaker") == "B" and (
                    line.get("open_up", False) or line.get("open_down", False)
                ))
            ):
                continue

            line = lines[line_id]
            dfs(line["down"] if line["up"] == bus else line["up"])

    dfs(start_bus)

    return affected_buses

def isolate_and_find_faulted_buses(faulted_line_id, lines, buses):
    """
    Isolates the faulted line by opening the appropriate disconnectors and possibly
    maintain breakers in open state, and finds all buses that are faulted as a result
    of the isolation.
    
    args:
        faulted_line_id: ID of the line where the fault occurred
        lines: dictionary of line data
        buses: dictionary of bus data

    returns:
        A set of bus IDs that are faulted as a result of the isolation.
    """

    faulted_buses = set()
    boundary_edges = [] 

    faulted_line = lines[faulted_line_id]
    faulted_line_breaker = faulted_line.get("breaker", "N")
    faulted_line_disconnector = faulted_line.get("disc", "N")
        
    def dfs(bus):
        if bus in faulted_buses:
            return

        faulted_buses.add(bus)

        for line_id in buses[bus]["connected_lines"]:
            line = lines[line_id]

            next_bus = line["down"] if line["up"] == bus else line["up"] 

            if line["disc"] == "N" and line["breaker"] not in ("U", "D", "B"):
                dfs(next_bus)

            else:
                if next_bus not in faulted_buses:
                    boundary_edges.append((bus, line_id))

    if faulted_line_disconnector == "B":
        faulted_line["open_up"] = True
        faulted_line["open_down"] = True
        return faulted_buses

    if faulted_line_breaker == "U" and faulted_line_disconnector == "D":
        faulted_line["open_down"] = True
        return faulted_buses
    

    start_buses = []
    if faulted_line_breaker == "U":
        start_buses.append(faulted_line["down"])
    elif faulted_line_breaker == "D":
        start_buses.append(faulted_line["up"])

    elif faulted_line_breaker == "N":
        if faulted_line_disconnector in ("N", "D"):
            start_buses.append(faulted_line["up"])
        if faulted_line_disconnector in ("N", "U"):
            start_buses.append(faulted_line["down"])

    for bus in start_buses:
        dfs(bus)

    for bus, line_id in boundary_edges:
        line = lines[line_id]
        disconnector = line["disc"]

        if disconnector == "U":
            line["open_up"] = True
        elif disconnector == "D":
            line["open_down"] = True
        elif disconnector == "B":
            if bus == line["up"]:
                line["open_up"] = True
            else:
                line["open_down"] = True

    return faulted_buses

def identify_unused_protection(protection_line_id, lines, faulted_buses):
    
    """
    Identifies the protection device on the given line if it was tripped but
    is not needed for isolation anymore.

    args:
        protection_line_id: ID of the line where the protection device is tripped
        lines: dictionary of line data
        faulted_buses: set of faulted bus IDs
    
    returns:
        None
    """

    if protection_line_id is None:
        return

    line = lines[protection_line_id]

    if line.get("fault"):
        return

    if (line["up"] in faulted_buses) ^ (line["down"] in faulted_buses):
        return

    line.pop("open_up", None)
    line.pop("open_down", None)
