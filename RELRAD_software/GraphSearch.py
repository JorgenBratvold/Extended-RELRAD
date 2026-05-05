import pandas as pd

'''
RELRAD-software, general software for reliability studies of radial power systems
    Copyright (C) 2025  Sondre Modalsli Aaberg

    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with this program.  If not, see <https://www.gnu.org/licenses/>.
'''

# Function to simulate the tripping of protection devices based on a fault
def tripProtection(fault, buses, sections):
    """
    Simulates the tripping of protection devices based on a fault.

    Args:
        fault (int): The faulted section.
        buses (DataFrame): Data about buses in the system.
        sections (DataFrame): Data about sections in the system.

    Returns:
        tuple: Updated buses, sections, tripped protection details, and failure status.
    """
    section = fault
    # Check if the faulted section has upstream or bidirectional protection
    if sections['Fuse/breaker direction'][section] in ['U', 'B']:
        # Trip the upstream protection and update the buses and sections
        trippedProtection = {
            'section': section,
            'bus': sections['Upstream Bus'][section],
            'direction': 'U'
        }
        buses['Downstream Sections'][sections['Upstream Bus'][section]].remove(section)
        sections['Upstream Bus'][section] = 0
        return buses, sections, trippedProtection, False

    # Move to the upstream section to find protection
    section = buses['Upstream Section'][sections['Upstream Bus'][section]]
    while True:
        if section == 0:
            # If no protection is found, return failure
            return 0, 0, 0, True
        if sections['Fuse/breaker direction'][section] != 'N':
            # Check if the section has downstream or bidirectional protection
            if sections['Fuse/breaker direction'][section] in ['D', 'B']:
                trippedProtection = {
                    'section': section,
                    'bus': sections['Downstream Bus'][section],
                    'direction': 'D'
                }
                # Update buses and sections after tripping downstream protection
                buses['Upstream Section'][sections['Downstream Bus'][section]] = 0
                buses['Connected Sections'][sections['Downstream Bus'][section]].remove(section)
                sections['Downstream Bus'][section] = 0
                return buses, sections, trippedProtection, False
            else:
                # Trip upstream protection
                trippedProtection = {
                    'section': section,
                    'bus': sections['Upstream Bus'][section],
                    'direction': 'U'
                }
                buses['Downstream Sections'][sections['Upstream Bus'][section]].remove(section)
                buses['Connected Sections'][sections['Upstream Bus'][section]].remove(section)
                sections['Upstream Bus'][section] = 0
                return buses, sections, trippedProtection, False
        else:
            # Continue searching upstream for protection
            section = buses['Upstream Section'][sections['Upstream Bus'][section]]

def findProtection(bus, buses, sections):
    """
    Finds the protection device for a given bus.

    Args:
        bus (int): The bus to find protection for.
        buses (DataFrame): Data about buses in the system.
        sections (DataFrame): Data about sections in the system.

    Returns:
        dict: Details of the protection device.
    """
    section = buses['Upstream Section'][bus]
    if sections['Fuse/breaker direction'][section] in ['U', 'B']:
        protection = {'section': section, 'bus': sections['Upstream Bus'][section], 'direction': 'U'}
        return protection
    else:
        section = buses['Upstream Section'][sections['Upstream Bus'][section]]
    while True:
        if sections['Fuse/breaker direction'][section] != 'N':
            if sections['Fuse/breaker direction'][section] in ['D', 'B']:
                protection = {'section': section, 'bus': sections['Downstream Bus'][section], 'direction': 'D'}
                return protection
            else:
                protection = {'section': section, 'bus': sections['Upstream Bus'][section], 'direction': 'U'}
                return protection
        else:
            section = buses['Upstream Section'][sections['Upstream Bus'][section]]

def DFS(bus, buses, sections, connected=[]):
    """
    Depth First Search (DFS) to find all connected buses.

    Args:
        bus (int): The starting bus.
        buses (DataFrame): Data about buses in the system.
        sections (DataFrame): Data about sections in the system.
        connected (list, optional): List of already connected buses. Defaults to [].

    Returns:
        list: List of connected buses.
    """
    if bus in connected:
        return connected
    if bus != 0:
        connected.append(bus)
    for i in buses['Connected Sections'][bus]:
        if i == 0:
            return connected
        if sections['Upstream Bus'][i] == bus:
            nextBus = sections['Downstream Bus'][i]
        else:
            nextBus = sections['Upstream Bus'][i]
        if nextBus == 0:
            continue
        if nextBus not in connected:
            connected = DFS(nextBus, buses, sections, connected)
    return connected

def connectedBetween(startBus, endBus, buses, sections, connected=[]):
    """
    Finds all buses connected between two given buses.

    Args:
        startBus (int): The starting bus.
        endBus (int): The ending bus.
        buses (DataFrame): Data about buses in the system.
        sections (DataFrame): Data about sections in the system.
        connected (list, optional): List of already connected buses. Defaults to [].

    Returns:
        list: List of connected buses between startBus and endBus.
    """
    if startBus in connected:
        return connected
    connected.append(startBus)
    for i in buses['Connected Sections'][startBus]:
        if i == 0:
            return connected
        if sections['Upstream Bus'][i] == startBus:
            nextBus = sections['Downstream Bus'][i]
        else:
            nextBus = sections['Upstream Bus'][i]
        if nextBus == 0:
            continue
        if nextBus == endBus:
            continue
        if nextBus not in connected:
            connected = connectedBetween(nextBus, endBus, buses, sections, connected)
    return connected

def disconnectorsDFS(bus, buses, sections, connected=[], disconnectors=[]):
    """
    Depth First Search (DFS) to find all disconnectors.

    Args:
        bus (int): The starting bus.
        buses (DataFrame): Data about buses in the system.
        sections (DataFrame): Data about sections in the system.
        connected (list, optional): List of already connected buses. Defaults to [].
        disconnectors (list, optional): List of already found disconnectors. Defaults to [].

    Returns:
        list: List of disconnectors.
    """
    if bus in connected:
        return disconnectors
    if bus != 0:
        connected.append(bus)
    for i in buses['Connected Sections'][bus]:
        if i == 0:
            continue

        if sections['Disconnector direction'][i] != 'N':
            disconnectors.append({
                'line': i,
                'fromBus': bus,
                's': sections['s'][i],
                'toBus': sections['Downstream Bus'][i] if sections['Upstream Bus'][i] == bus else sections['Upstream Bus'][i]
            })
            continue

        if sections['Upstream Bus'][i] == bus:
            nextBus = sections['Downstream Bus'][i]
        else:
            nextBus = sections['Upstream Bus'][i]

        if nextBus == 0:
            continue

        if nextBus not in connected:
            disconnectors = disconnectorsDFS(nextBus, buses, sections, connected, disconnectors)
    return disconnectors

def disconnect(fault, buses, sections):
    """
    Disconnects sections based on a fault.

    Args:
        fault (int): The faulted section.
        buses (DataFrame): Data about buses in the system.
        sections (DataFrame): Data about sections in the system.

    Returns:
        tuple: Updated buses, sections, and list of disconnectors.
    """
    if sections['Disconnector direction'][fault] == 'B':
        faultBus = 0
        disconnectors = []
        disconnectors.append({
                'line': fault,
                'fromBus': sections['Upstream Bus'][fault],
                's': sections['s'][fault],
                'toBus': sections['Downstream Bus'][fault]
            })
        disconnectors.append({
                'line': fault,
                'fromBus': sections['Downstream Bus'][fault],
                's': sections['s'][fault],
                'toBus': sections['Upstream Bus'][fault]
            })
    elif sections['Disconnector direction'][fault] == 'D' and sections['Upstream Bus'][fault] == 0:
        faultBus = 0
        disconnectors = []
        disconnectors.append({
                'line': fault,
                'fromBus': sections['Downstream Bus'][fault],
                's': sections['s'][fault],
                'toBus': sections['Upstream Bus'][fault]
            })
    elif sections['Disconnector direction'][fault] == 'U':
        faultBus = sections['Downstream Bus'][fault]
    elif sections['Disconnector direction'][fault] == 'D':
        faultBus = sections['Upstream Bus'][fault]
    else:
        faultBus = sections['Downstream Bus'][fault]
        if faultBus == 0:
            faultBus = sections['Upstream Bus'][fault]
    if faultBus != 0:
        disconnectors = disconnectorsDFS(faultBus, buses, sections, connected=[], disconnectors=[])

    openDisconnectors = []
    for i in disconnectors:
        if i['fromBus'] == sections['Upstream Bus'][i['line']]:
            if sections['Disconnector direction'][i['line']] in ['D', 'B']:
                openDisconnectors.append({'section': i['line'], 'direction': 'D'})
                buses['Upstream Section'][sections['Downstream Bus'][i['line']]] = 0
                if i['line'] in buses['Connected Sections'][sections['Downstream Bus'][i['line']]]:
                    buses['Connected Sections'][sections['Downstream Bus'][i['line']]].remove(i['line'])
                sections['Downstream Bus'][i['line']] = 0
            else:
                openDisconnectors.append({'section': i['line'], 'direction': 'U'})
                if i['line'] in buses['Downstream Sections'][sections['Upstream Bus'][i['line']]]:
                    buses['Downstream Sections'][sections['Upstream Bus'][i['line']]].remove(i['line'])
                if i['line'] in buses['Connected Sections'][sections['Upstream Bus'][i['line']]]:
                    buses['Connected Sections'][sections['Upstream Bus'][i['line']]].remove(i['line'])
                sections['Upstream Bus'][i['line']] = 0
        else:
            if sections['Disconnector direction'][i['line']] in ['U', 'B']:
                openDisconnectors.append({'section': i['line'], 'direction': 'U'})
                if i['line'] in buses['Downstream Sections'][sections['Upstream Bus'][i['line']]]:
                    buses['Downstream Sections'][sections['Upstream Bus'][i['line']]].remove(i['line'])
                if i['line'] in buses['Connected Sections'][sections['Upstream Bus'][i['line']]]:
                    buses['Connected Sections'][sections['Upstream Bus'][i['line']]].remove(i['line'])
                sections['Upstream Bus'][i['line']] = 0
            else:
                openDisconnectors.append({'section': i['line'], 'direction': 'D'})
                buses['Upstream Section'][sections['Downstream Bus'][i['line']]] = 0
                if i['line'] in buses['Connected Sections'][sections['Downstream Bus'][i['line']]]:
                    buses['Connected Sections'][sections['Downstream Bus'][i['line']]].remove(i['line'])
                sections['Downstream Bus'][i['line']] = 0

    return buses, sections, disconnectors

def protectionNeededTestDFS(bus, buses, sections, protection, connected, needed):
    """
    Depth First Search (DFS) to test if protection is needed.

    Args:
        bus (int): The starting bus.
        buses (DataFrame): Data about buses in the system.
        sections (DataFrame): Data about sections in the system.
        protection (dict): Details of the protection device.
        connected (list): List of already connected buses.
        needed (bool): Flag indicating if protection is needed.

    Returns:
        bool: True if protection is needed, False otherwise.
    """
    if bus in connected:
        return needed
    connected.append(bus)
    if bus == protection['bus']:
        needed = True
        return needed
    for i in buses['Connected Sections'][bus]:
        if i == protection['section']:
            needed = True
            return needed
        if i == 0:
            return needed
        if sections['Upstream Bus'][i] == bus:
            nextBus = sections['Downstream Bus'][i]
        else:
            nextBus = sections['Upstream Bus'][i]
        if nextBus == 0:
            continue
        if nextBus not in connected:
            needed = protectionNeededTestDFS(nextBus, buses, sections, protection, connected, needed)
    return needed

def reconnectProtection(buses, sections, trippedProtection, fault):
    """
    Reconnects protection devices after a fault.

    Args:
        buses (DataFrame): Data about buses in the system.
        sections (DataFrame): Data about sections in the system.
        trippedProtection (dict): Details of the tripped protection device.
        fault (int): The faulted section.

    Returns:
        tuple: Updated buses and sections.
    """
    if sections['Upstream Bus'][fault] != 0:
        if protectionNeededTestDFS(sections['Upstream Bus'][fault], buses, sections, trippedProtection, connected=[], needed=False):
            return buses, sections
    elif sections['Downstream Bus'][fault] != 0:
        if protectionNeededTestDFS(sections['Downstream Bus'][fault], buses, sections, trippedProtection, connected=[], needed=False):
            return buses, sections
    if trippedProtection['direction'] == 'U':
        sections.loc[trippedProtection['section'], 'Upstream Bus'] = trippedProtection['bus']
        buses['Downstream Sections'][trippedProtection['bus']].append(trippedProtection['section'])
        buses['Connected Sections'][trippedProtection['bus']].append(trippedProtection['section'])
    else:
        sections.loc[trippedProtection['section'], 'Downstream Bus'] = trippedProtection['bus']
        buses['Upstream Section'][trippedProtection['bus']] = trippedProtection['section']
        buses['Connected Sections'][trippedProtection['bus']].append(trippedProtection['section'])
    return buses, sections

def findLPbetweenBusAndProtection(bus, buses, sections):
    """
    Finds the load points between a bus and its protection device.

    Args:
        bus (int): The starting bus.
        buses (DataFrame): Data about buses in the system.
        sections (DataFrame): Data about sections in the system.
    """
    section = buses['Upstream Section'][bus]
    while True:
        if sections['Fuse/breaker direction'][section] != 'N':
            if sections['Fuse/breaker direction'][section] in ['D', 'B']:
                bus = sections['Downstream Bus'][section]
            else:
                bus = sections['Upstream Bus'][section]
        else:
            section = buses['Upstream Section'][sections['Upstream Bus'][section]]

def findConnectedSegments(buses, sections):
    """
    Finds all connected segments in the system.

    Args:
        buses (DataFrame): Data about buses in the system.
        sections (DataFrame): Data about sections in the system.

    Returns:
        list: List of connected segments.
    """
    nrFound = 0
    found = []
    connections = []
    connected = []
    while nrFound < len(buses):
        for j, row in buses.iterrows():
            if j not in found:
                connected = []
                connected = DFS(j, buses, sections, connected=[])
                connections.append(connected.copy())
                for n in connected:
                    nrFound += 1
                    found.append(n)
    return connections

def findBackupFeeders(connections, backupFeeders):
    """
    Finds backup feeders for connected segments.

    Args:
        connections (list): List of connected segments.
        backupFeeders (DataFrame): Data about backup feeders in the system.

    Returns:
        list: List of connections with backup feeders.
    """
    conectionsWithBackup = []
    for i in connections:
        for n, row in backupFeeders.iterrows():
            if i == backupFeeders['End 1'][n] or i == backupFeeders['End 2'][n]:
                bus = i
                backupFeeder = n
                if i == backupFeeders['End 1'][n]:
                    otherEnd = backupFeeders['End 2'][n]
                else:
                    otherEnd = backupFeeders['End 1'][n]
                conectionsWithBackup.append({
                    'bus': bus,
                    'backupFeeder': backupFeeder,
                    'connection': connections,
                    'otherEnd': otherEnd
                })
    return conectionsWithBackup

def mainPower(bus, buses, sections, generationData):
    """
    Checks if a bus is connected to the main power feeder.

    Args:
        bus (int): The bus to check.
        buses (DataFrame): Data about buses in the system.
        sections (DataFrame): Data about sections in the system.
        generationData (DataFrame): Data about generation in the system.

    Returns:
        bool: True if the bus is connected to the main power feeder, False otherwise.
    """
    while True:
        if bus in generationData.index:
            if generationData['Main Feeder'][bus]:
                return True
        if buses['Upstream Section'][bus] == 0:
            return False
        if sections['Upstream Bus'][buses['Upstream Section'][bus]] == 0:
            return False
        bus = sections['Upstream Bus'][buses['Upstream Section'][bus]]

def findLoadPoints(connections, loads):
    """
    Finds load points in connected segments.

    Args:
        connections (list): List of connected segments.
        loads (DataFrame): Data about loads in the system.

    Returns:
        list: List of load points.
    """
    loadPoints = []
    for i, row in loads.iterrows():
        if i in connections:
            loadPoints.append(i)
    return loadPoints

def switchingTime(connectedSections, switchingTimes):
    """
    Finds the switching time for connected sections.

    Args:
        connectedSections (list): List of connected sections.
        switchingTimes (dict): Dictionary of switching times.

    Returns:
        int: The switching time.
    """
    for i in connectedSections:
        if i in switchingTimes:
            return switchingTimes[i]





