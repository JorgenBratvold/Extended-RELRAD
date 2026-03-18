import pandas as pd
import random as rng
import numpy as np
import copy
import GraphSearch as gs

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

def fixbuses(buses, sections):
    """
    Updates the buses DataFrame with upstream, downstream, and connected sections.

    Args:
        buses (DataFrame): Data about buses in the system.
        sections (DataFrame): Data about sections in the system.

    Returns:
        DataFrame: Updated buses DataFrame with populated connectivity information.
    """
    for bus_id, _ in buses.iterrows():
        upstream_section = 0
        downstream_sections = []
        for section_id, _ in sections.iterrows():
            if sections['Upstream Bus'][section_id] == bus_id:
                downstream_sections.append(section_id)
            if sections['Downstream Bus'][section_id] == bus_id:
                upstream_section = section_id
        buses['Upstream Section'][bus_id] = upstream_section
        buses['Downstream Sections'][bus_id] = downstream_sections
        buses['Connected Sections'][bus_id] = downstream_sections.copy()
        buses['Connected Sections'][bus_id].append(upstream_section)
    return buses


def calcFailRates(sections, components):
    """
    Calculates and assigns failure rates and component properties for each section.
    
    Args:
        sections (DataFrame): Contains section data including cable types and transformers
        components (DataFrame): Contains reliability data (λ, r, s values) for each component type
    
    Returns:
        DataFrame: Updated sections with calculated failure rates and component properties
    """
    for i, row in sections.iterrows():
        # Dictionary to store component properties for this section
        secComponents = {}
        
        # Calculate line (cable) properties including length-dependent failure rate
        secComponents['line'] = {
            'type': sections['Cable Type'][i],
            'length': sections['Length'][i],
            'lambda': components['lambda'][sections['Cable Type'][i]] * sections['Length'][i],  # Failure rate per year
            'r': components['r'][sections['Cable Type'][i]],  # Repair time in hours
            's': components['s'][sections['Cable Type'][i]]   # Switching time in hours
        }
        
        # Add transformer properties if section contains transformers
        if sections['Nr Transformers'][i]:
            secComponents['transformer'] = {
                'type': sections['Transformer Type'][i],
                'lambda': components['lambda'][sections['Transformer Type'][i]] * sections['Nr Transformers'][i],
                'r': components['r'][sections['Transformer Type'][i]],
                's': components['s'][sections['Transformer Type'][i]]
            }
        
        # Update section properties
        sections['s'][i] = components['s'][sections['Cable Type'][i]]
        sections['Components'][i] = secComponents
    return sections

def GenerateHistory(l, r):
    """
    Generates random Time To Failure (TTF) and Time To Repair (TTR) using exponential distribution.
    
    Args:
        l (float): Failure rate (lambda) in failures per year
        r (float): Mean repair time in hours
    
    Returns:
        tuple: (TTF in hours, TTR in hours)
    """
    # Generate TTF using inverse transform sampling
    # 8736 converts from years to hours (365.25 * 24 = 8736)
    TTF = (-1/l) * np.log(rng.uniform(0, 0.999)) * 8736
    
    # Generate TTR using exponential distribution
    TTR = -r * np.log(rng.uniform(0, 0.999))
    return TTF, TTR

def minTTF(history):
    """
    Finds the component with the earliest Time To Failure in the failure history.
    
    Args:
        history (dict): Dictionary containing failure history for all components
            Keys: Component IDs
            Values: Dictionary containing TTF, TTR, and other component properties
    
    Returns:
        str: ID of the component with the minimum TTF
    """
    # Initialize with the first component's TTF
    TTFcomponent = next(iter(history))
    TTF = history[TTFcomponent]['TTF']
    
    # Find component with minimum TTF
    for secComp in history:
        if history[secComp]['TTF'] < TTF:
            TTFcomponent = secComp
            TTF = history[secComp]['TTF']
    return TTFcomponent

def MonteCarloYear(sectionsOriginal, busesOriginal, loads, generationData, backupFeeders):
    """
    Simulates one year of system operation using Monte Carlo method.
    
    Args:
        sectionsOriginal (DataFrame): Original section data
        busesOriginal (DataFrame): Original bus data
        loads (DataFrame): Load point data
        generationData (dict): Generation system parameters
        backupFeeders (list): Available backup feeders
    
    Returns:
        dict: Results containing number of faults and unavailability for each load point
    """
    h = 8736  # Total hours in a year
    results = {}
    for i in loads.index:
        results[i] = {'nrOfFaults': 0, 'U': 0}
    history = {}
        # Generate failure history for each component
    for sec, row in sectionsOriginal.iterrows():
        for comp in sectionsOriginal['Components'][sec]:
            TTF, TTR = GenerateHistory(sectionsOriginal['Components'][sec][comp]['lambda'], sectionsOriginal['Components'][sec][comp]['r'])
            history[sec + comp] = {
                'sec': sec,
                'comp': comp,
                'TTF': TTF,
                'TTR': TTR,
                'l': sectionsOriginal['Components'][sec][comp]['lambda'],
                'r': sectionsOriginal['Components'][sec][comp]['r']}

        # Find the first fault to occur
    fault = minTTF(history)
    while history[fault]['TTF'] < h:
            # Create deep copies of the original data for analysis
        sectionsCopy = pd.DataFrame(columns=sectionsOriginal.columns,
                                    data=copy.deepcopy(sectionsOriginal.values),
                                    index=sectionsOriginal.index)
        busesCopy = pd.DataFrame(columns=busesOriginal.columns,
                                    data=copy.deepcopy(busesOriginal.values),
                                    index=busesOriginal.index)
            
            # Calculate the effects of faults on load points
        effectOnLPs = gs.faultEffects(history[fault]['sec'], history[fault]['comp'], busesCopy, sectionsCopy, loads, generationData, backupFeeders, history[fault]['TTR'])
            
        for LP in effectOnLPs:
            if effectOnLPs[LP] > 0:
                # Update load point data
                results[LP]['nrOfFaults'] += 1
                results[LP]['U'] += effectOnLPs[LP]

        # Generate new failure history for the faulted component
        newTTF, newTTR = GenerateHistory(history[fault]['l'], history[fault]['r'])

        history[fault]['TTF'] += newTTF + history[fault]['TTR']
        history[fault]['TTR'] = newTTR
        fault = minTTF(history)
    return results