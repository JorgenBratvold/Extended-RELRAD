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

def createSystem(file_path, LoadCurve = False):
    """
    Creates the system by reading data from Excel files.

    Args:
        file_path (str): Path to the Excel file containing system data.

    Returns:
        dict: A dictionary containing data about buses, sections, loads, components, backup feeders, and generation.
    """
    system = {}
    # Load data for buses, sections, loads, components, backup feeders, and generation
    system['buses'] = pd.read_excel(file_path, 'Bus Data', index_col=0)
    system['sections'] = pd.read_excel(file_path, 'Line Data', index_col=0)
    system['loads'] = pd.read_excel(file_path, 'Load Point Data', index_col=0)
    system['components'] = pd.read_excel(file_path, 'Component Data', index_col=0)
    system['backupFeeders'] = pd.read_excel(file_path, 'Backup Feeders', index_col=0)
    system['generationData'] = pd.read_excel(file_path, 'Generation Data', index_col=0)

    # Initialize columns for buses and sections
    system['buses']['Upstream Section'] = str(0)
    system['buses']['Downstream Sections'] = [list() for i in range(len(system['buses'].index))]
    system['buses']['Connected Sections'] = [list() for i in range(len(system['buses'].index))]
    system['sections']['s'] = float(0)
    system['sections']['Components'] = {}

    # Initialize columns for loads
    system['loads']['U'] = float(0)
    system['loads']['nrOfFaults'] = int(0)
    system['loads']['R'] = float(0)
    system['loads']['Lambda'] = float(0)
    if LoadCurve:
        system['loads']['ENS'] = float(0)

    # Fix buses and calculate failure rates
    system['buses'] = fixbuses(system['buses'], system['sections'])
    system['sections'] = calcFailRates(system['sections'], system['components'])

    if LoadCurve:
        # Load load curve data from Excel file
        loadCurveData = {}
        loadCurveData['weeklyFactor'] = pd.read_excel(file_path, 'Weekly Load Factor', index_col=0)
        loadCurveData['dailyFactor'] = pd.read_excel(file_path, 'Daily Load Factor', index_col=0)
        loadCurveData['hourlyFactor'] = pd.read_excel(file_path, 'Hourly Load Factor', index_col=0)
        system['loadCurveData'] = loadCurveData
    return system



def fixbuses(buses, sections):
    """
    Updates the buses DataFrame with upstream, downstream, and connected sections.

    Args:
        buses (DataFrame): Data about buses in the system.
        sections (DataFrame): Data about sections in the system.

    Returns:
        DataFrame: Updated buses DataFrame.
    """
    for bus in buses.index:
        upstream_section = 0
        downstream_sections = []
        for section in sections.index:
            if sections['Upstream Bus'][section] == bus:
                downstream_sections.append(section)
            if sections['Downstream Bus'][section] == bus:
                upstream_section = section
        buses['Upstream Section'][bus] = upstream_section
        buses['Downstream Sections'][bus] = downstream_sections
        buses['Connected Sections'][bus] = downstream_sections.copy()
        buses['Connected Sections'][bus].append(upstream_section)
    return buses



def calcFailRates(sections, components):
    """    
    Calculates failure rates for each section based on the components used.
    Args:
        sections (DataFrame): Data about sections in the system.
        components (DataFrame): Data about components used in the system.
    Returns:
        DataFrame: Updated sections DataFrame with failure rates.
    """
    for i, row in sections.iterrows():
        secComponents = {}
        if sections['Cable Type'][i]:
            secComponents['line'] = {'type': sections['Cable Type'][i], 'length': sections['Length'][i], 'lambda': components['lambda'][sections['Cable Type'][i]] * sections['Length'][i], 'r': components['r'][sections['Cable Type'][i]], 's': components['s'][sections['Cable Type'][i]]}
            sections['s'][i] = components['s'][sections['Cable Type'][i]]
        else:
            secComponents['line'] = {'type': 'None', 'length': 0, 'lambda': 0, 'r': 0, 's': 0}
            sections['s'][i] = 0
        if sections['Nr Transformers'][i]:
            secComponents['transformer'] = {'type': sections['Transformer Type'][i], 'lambda': components['lambda'][sections['Transformer Type'][i]] * sections['Nr Transformers'][i], 'r': components['r'][sections['Transformer Type'][i]], 's': components['s'][sections['Transformer Type'][i]]}
        #if sections['Nr Breaker'][i]: #if relaiability of breakes is to be included, uncomment this line
            #sections.iloc[i,'lambda'] += components['lambda'][sections['Breaker Type'][i]] * sections['Nr Breaker'][i]
        sections['Components'][i] = secComponents
    return sections


