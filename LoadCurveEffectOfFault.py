import pandas as pd
import GraphSearch as gs
import MiscFunctions as mf
import GenerationFunctions as gf
import LoadCurve as lc

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

def loadCurveFaultEffects(fault, component, buses, sections, loads, generationData, backupFeeders, t, r, loadCurve=0, DERScurve = 0, DSEBF = True, RNG=False, DERS = False):
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

    # If the entire system is down, return fault duration for all load points
    if fullSystemDown:
        effectsOnLPs = {}
        for i, row in loads.iterrows():
            effectsOnLPs[i] = r
        return effectsOnLPs

    # Isolate the faulted section and identify disconnectors
    buses, sections, disconnectors = gs.disconnect(fault, buses, sections)

    # Determine the maximum switching time among disconnectors
    s = 0
    for i in disconnectors:
        if i['s'] > s:
            s = i['s']

    r = max(s, r) #Sets a lower bound  of r at the switching time (mostly error prevention)

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

    # Record the effects on disconnected sections
    for i in disconnectedSections:
        effectsOnSections.append({
            'state': 'tripped',
            'loads': gs.findLoadPoints(i, loads),
            'time': gs.switchingTime(i, switchingTimes),
            'ENS': lc.loadCurveSumEnergy(t, gs.switchingTime(i, switchingTimes), gs.findLoadPoints(i, loads), loads, loadCurve)
        })

    # Reconnect protection devices and update the system state
    buses, sections = gs.reconnectProtection(buses, sections, trippedProtection, fault)

    # Identify disconnected sections again after reconnection
    disconnectedSections = gs.findConnectedSegments(buses, sections)

    for i in disconnectedSections:
        if sections['Upstream Bus'][fault] in i or sections['Downstream Bus'][fault] in i:
            # Faulted section
            effectsOnSections.append({
                'state': 'fault',
                'loads': gs.findLoadPoints(i, loads),
                'time': r,
                'ENS': lc.loadCurveSumEnergy(t, r, gs.findLoadPoints(i, loads), loads, loadCurve)
            })
        elif gs.mainPower(i[0], buses, sections, generationData):
            # Section connected to the main power source
            effectsOnSections.append({
                'state': 'connected',
                'loads': gs.findLoadPoints(i, loads),
                'time': 0,
                'ENS': 0
            })
        else:
            if DERS:
                if DERScurve:
                    ENS, uBackup = lc.LCandDERScurve(t, r, s, gs.findLoadPoints(i, loads), loads, loadCurve, generationData, i , DERScurve)
                else:
                    uBackup = gf.loadCurveDistributedGeneration(
                            lc.loadCurveSumEnergy(t+s, r-s, gs.findLoadPoints(i, loads), loads, loadCurve),
                            lc.loadPeak(t+s, r-s, gs.findLoadPoints(i, loads), loads, loadCurve),
                            generationData, 
                            i, 
                            r,
                            s) #Calculates the outage duration after local generation is utilized
            else:
                uBackup = r
            
            # Check for backup feeders
            connectedBackup = gs.findBackupFeeders(i, backupFeeders)
            if connectedBackup:
                for j in connectedBackup:
                    if gs.mainPower(j['otherEnd'], buses, sections, generationData):
                        if backupFeeders.at[j['backupFeeder'], 's'] < uBackup:
                            breaker = gs.findProtection(j['otherEnd'], buses, sections)
                            effectsOnSections.append({
                                'state': 'backupPower',
                                'loads': gs.findLoadPoints(i, loads),
                                'time': backupFeeders['s'][j['backupFeeder']],
                                'ENS': lc.loadCurveSumEnergy(t, backupFeeders['s'][j['backupFeeder']], gs.findLoadPoints(i, loads), loads, loadCurve)
                            })
                            if DSEBF:
                                if breaker['direction'] == 'D':
                                    endBus = sections['Upstream Bus'][breaker['section']]
                                else:
                                    endBus = breaker['bus']
                                connected = gs.connectedBetween(j['otherEnd'], endBus, buses, sections, connected=[])
                                effectsOnSections.append({
                                    'state': 'backup',
                                    'loads': gs.findLoadPoints(connected, loads),
                                    'time': s,
                                    'ENS': lc.loadCurveSumEnergy(t, s, gs.findLoadPoints(connected, loads), loads, loadCurve)
                                })
                        elif DERS:
                            # If DERS are enabled and are prefferential to BF, use local generation
                            if DERScurve:
                                effectsOnSections.append({
                                'state': 'localGenerationOverBF',
                                'loads': gs.findLoadPoints(i, loads),
                                'time': uBackup,
                                'ENS': ENS
                                })
                            else:
                                effectsOnSections.append({
                                    'state': 'localGenerationOverBF',
                                    'loads': gs.findLoadPoints(i, loads),
                                    'time': uBackup,
                                    'ENS': lc.loadCurveSumEnergy(t, uBackup, gs.findLoadPoints(i, loads), loads, loadCurve)
                                })
            elif DERS and uBackup < r:
                # If no backup feeder is available, use local generation
                if DERScurve:
                    effectsOnSections.append({
                                'state': 'localGenerationOverBF',
                                'loads': gs.findLoadPoints(i, loads),
                                'time': uBackup,
                                'ENS': ENS
                                })
                else:
                    effectsOnSections.append({
                                'state': 'localGenerationOverBF',
                                'loads': gs.findLoadPoints(i, loads),
                                'time': uBackup,
                                'ENS': lc.loadCurveSumEnergy(t, uBackup, gs.findLoadPoints(i, loads), loads, loadCurve)
                                })
            else:
                # No backup feeder available
                effectsOnSections.append({
                    'state': 'noBackup',
                    'loads': gs.findLoadPoints(i, loads),
                    'time': r,
                    'ENS': lc.loadCurveSumEnergy(t, r, gs.findLoadPoints(i, loads), loads, loadCurve)
                })



    #print('Effects on sections:', effectsOnSections)

    
    # Aggregate the effects on load points
    ''''
    ENS = 0
    effectsOnLPs = {}
    for LP in loads.index:
        LPeffects = {'U': 0, 'ENS': 0}
        effectsOnLPs[LP] = LPeffects
    for sec in effectsOnSections:
        ENS += sec['ENS']
        for LP in sec['loads']:
            if sec['time'] is None:
                sec['time'] = 0
            if sec['time'] > effectsOnLPs[LP]['U']:
                effectsOnLPs[LP]['U'] = sec['time']
    '''

    ENS = 0
    effectsOnLPs = {}
    for sec in effectsOnSections:
        ENS += sec['ENS']
        for LP in sec['loads']:
            if LP in effectsOnLPs:
                if sec['time'] is None:
                    sec['time'] = 0
                elif sec['time'] > effectsOnLPs[LP]:
                    effectsOnLPs[LP] = sec['time']
            else:
                if sec['time'] is None:
                    effectsOnLPs[LP] = 0
                else:
                    effectsOnLPs[LP] = sec['time']



    # Return the final effects on load points
    #print('Effects on load points:', effectsOnLPs)
    return effectsOnLPs, ENS


