import pandas as pd
import GraphSearch as gs
import MiscFunctions as mf
import GenerationFunctions as gf


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

def faultEffects(fault, component, buses, sections, loads, generationData, backupFeeders, r, loadCurve=0, DSEBF = True, RNG=False, DERS = False, createFIM=False):
    """
    Calculates the effects of a fault on the system.

    Args:
        fault (int): The faulted section.
        component (str): The component affected by the fault (not in use anymore).
        buses (DataFrame): Data about buses in the system.
        sections (DataFrame): Data about sections in the system.
        loads (DataFrame): Data about loads in the system.
        generationData (DataFrame): Data about generation in the system.
        backupFeeders (DataFrame): Data about backup feeders in the system.
        r (int): The fault duration.
        DSEBF (bool, optional): (Down Stream Effect of Backup Feeder) Flag indicating if backup feeders creates a outage on  the secondry side.
        RNG (bool, optional): Flag indicating if random number generation is used. Defaults to False.

    Returns:
        dict: Effects of the fault on load points.
    """

    # Initialize a list to store the effects on sections
    effectsOnSections = []

    # Trip protection devices and check if the entire system is down
    buses, sections, trippedProtection, fullSystemDown = gs.tripProtection(fault, buses, sections)

    #print('tripped protection', trippedProtection) #Debugging line

    # If the entire system is down, return fault duration for all load points
    if fullSystemDown:
        effectsOnLPs = {}
        effectsOnSections.append({
            'state': 'fullSystemDown',
            'loads': loads.index.tolist(),
            'time': r
        })
        for i, row in loads.iterrows():
            effectsOnLPs[i] = r
        if createFIM:
            return effectsOnLPs, effectsOnSections
        else:
            return effectsOnLPs

    # Isolate the faulted section and identify disconnectors
    buses, sections, disconnectors = gs.disconnect(fault, buses, sections)

    #print('disconnectors:', disconnectors)  #Debugging line

    # Determine the maximum switching time among disconnectors
    s = 0
    for i in disconnectors:
        if i['s'] > s:
            s = i['s']

    r = max(r, s)  # Ensure r is at least as long as the maximum switching time (mostly to avoid errors from negative values)

    # Calculate switching times for each bus
    switchingTimes = {}
    for i in disconnectors:
        if i['fromBus'] not in switchingTimes:
            switchingTimes[i['fromBus']] = i['s']
        else:
            if i['s'] > switchingTimes[i['fromBus']]:
                switchingTimes[i['fromBus']] = i['s']
        if i['toBus'] not in switchingTimes:
            switchingTimes[i['toBus']] = i['s']
        else:
            if i['s'] > switchingTimes[i['toBus']]:
                switchingTimes[i['toBus']] = i['s']

    # Identify all isolated interconnections in the system
    disconnectedSections = gs.findConnectedSegments(buses, sections)

    #print('disconnected sections:', disconnectedSections)  # Debugging line

    # Record the effects on disconnected sections
    for i in disconnectedSections:
        effectsOnSections.append({
            'state': 'tripped',
            'loads': gs.findLoadPoints(i, loads),
            'time': gs.switchingTime(i, switchingTimes)
        })

    # Reconnect protection devices and update the system state
    buses, sections = gs.reconnectProtection(buses, sections, trippedProtection, fault)

    #print('buses after reconnection:', buses)  # Debugging line
    #print('sections after reconnection:', sections)  # Debugging line

    # Identify disconnected sections again after reconnection
    disconnectedSections = []
    disconnectedSections = gs.findConnectedSegments(buses, sections)

    #print('disconnected sections after reconnection:', disconnectedSections)  # Debugging line

    for i in disconnectedSections:
        if sections['Upstream Bus'][fault] in i or sections['Downstream Bus'][fault] in i:
            # Faulted section
            effectsOnSections.append({
                'state': 'fault',
                'loads': gs.findLoadPoints(i, loads),
                'time': r
            })
        elif gs.mainPower(i[0], buses, sections, generationData):
            # Section connected to the main power source
            effectsOnSections.append({
                'state': 'connected',
                'loads': gs.findLoadPoints(i, loads),
                'time': 0
            })
        else: # Section not connected to the main power source or to the fault, checks for any type of backup power
            if DERS:
                uBackup = gf.distributedGeneration(loads, generationData, i, r, s) #Calculates the outage duration after local generation is utilized
            else:
                uBackup = r
            # Check for backup feeders
            connectedBackup = gs.findBackupFeeders(i, backupFeeders)
            if connectedBackup:
                for j in connectedBackup:
                    if gs.mainPower(j['otherEnd'], buses, sections, generationData): #checks if the backup feeder is connected to the main power source on the opposite end
                        if backupFeeders.at[j['backupFeeder'], 's'] < uBackup:
                            breaker = gs.findProtection(j['otherEnd'], buses, sections)
                            effectsOnSections.append({
                                'state': 'backupPower',
                                'loads': gs.findLoadPoints(i, loads),
                                'time': backupFeeders['s'][j['backupFeeder']]
                            })
                            if DSEBF: #Down Stream Effect of Backup Feeder
                                if breaker['direction'] == 'D':
                                    endBus = sections['Upstream Bus'][breaker['section']]
                                else:
                                    endBus = breaker['bus']
                                connected = gs.connectedBetween(j['otherEnd'], endBus, buses, sections, connected=[])
                                effectsOnSections.append({
                                    'state': 'backup',
                                    'loads': gs.findLoadPoints(connected, loads),
                                    'time': s
                                })
                        elif DERS:
                            # If DERS are enabled and are prefferential to BF, use local generation
                            effectsOnSections.append({
                                'state': 'localGenerationOverBF',
                                'loads': gs.findLoadPoints(i, loads),
                                'time': uBackup
                            })
            elif DERS and uBackup < r:
                # If no backup feeder is available, use local generation
                effectsOnSections.append({
                    'state': 'localGeneration',
                    'loads': gs.findLoadPoints(i, loads),
                    'time': uBackup
                })
            else:
                # No backup feeder available
                effectsOnSections.append({
                    'state': 'noBackup',
                    'loads': gs.findLoadPoints(i, loads),
                    'time': r
                })

    #print('Effects on sections:', effectsOnSections) #Intermediat debugging line
    


    # Aggregate the effects on load points
    effectsOnLPs = {}
    for i in effectsOnSections:
        for LP in i['loads']:
            if LP in effectsOnLPs:
                if i['time'] is None:
                    i['time'] = 0
                elif i['time'] > effectsOnLPs[LP]:
                    effectsOnLPs[LP] = i['time']
            else:
                if i['time'] is None:
                    effectsOnLPs[LP] = 0
                else:
                    effectsOnLPs[LP] = i['time']

    # Return the final effects on load points



    if createFIM:
        return effectsOnLPs, effectsOnSections
    else:
        return effectsOnLPs
