import pandas as pd
import EffectOfFault as ef
import CreateSystem as cs
import copy
from concurrent.futures import ThreadPoolExecutor

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

def RELRAD(loc, outFile, DSEBF=True, DERS=False, createFIM=False):

    #create system data
    system = cs.createSystem(loc)
    
    if createFIM:
        FIM = pd.DataFrame(columns=system['loads'].index, index=system['sections'].index)
    
    # Create a list of all components in the system
    componentList = []
    for sec in system['sections'].index:
        for comp in system['sections']['Components'][sec]:
            componentTag = sec + comp
            componentList.append(componentTag)

    # Create a list of load points (LPs) with different states
    LPs = []
    for i in system['loads'].index:
        LPs.append(i + 'l')  # Load point lambda
        LPs.append(i + 'r')  # Load point repair time
        LPs.append(i + 'U')  # Load point unavailability

    # Initialize a DataFrame to store results
    results = pd.DataFrame(index=componentList, columns=LPs)



    # Iterate through each section and component to calculate effects on load points
    for sec in system['sections'].index:
        for comp in system['sections']['Components'][sec]:
            print(sec, comp)
            # Create deep copies of the original data for analysis
            sectionsCopy = pd.DataFrame(columns=system['sections'].columns,
                                        data=copy.deepcopy(system['sections'].values),
                                        index=system['sections'].index)
            busesCopy = pd.DataFrame(columns=system['buses'].columns,
                                     data=copy.deepcopy(system['buses'].values),
                                     index=system['buses'].index)
            
            # Calculate the effects of faults on load points
            
            if createFIM:
                effectOnLPs, EOS = ef.faultEffects(sec, comp, busesCopy, sectionsCopy, system['loads'], system['generationData'], system['backupFeeders'], system['sections']['Components'][sec][comp]['r'], DSEBF=DSEBF, DERS=DERS, createFIM = createFIM)
                for i in EOS:
                    if i['state'] == 'fault':
                        for j in i['loads']:
                            FIM.at[sec, j] = 'F'
                    elif i['state'] == 'connected':
                        for j in i['loads']:
                            if effectOnLPs[j] == 0:
                                FIM.at[sec, j] = '0'
                            else:
                                FIM.at[sec, j] = 'M'
                    elif i['state'] == 'backupPower':
                        for j in i['loads']:
                            FIM.at[sec, j] = 'B'
                    elif i['state'] == 'noBackup':
                        for j in i['loads']:
                            FIM.at[sec, j] = 'N'
            else:
                effectOnLPs = ef.faultEffects(sec, comp, busesCopy, sectionsCopy, system['loads'], system['generationData'], system['backupFeeders'], system['sections']['Components'][sec][comp]['r'], DSEBF=DSEBF, DERS=DERS)
            
            componentTag = sec + comp
            for LP in effectOnLPs:
                if effectOnLPs[LP] > 0:
                    # Update results for the load point
                    results.loc[componentTag, LP + 'l'] = system['sections']['Components'][sec][comp]['lambda']
                    results.loc[componentTag, LP + 'r'] = effectOnLPs[LP]
                    results.loc[componentTag, LP + 'U'] = system['sections']['Components'][sec][comp]['lambda'] * effectOnLPs[LP]
                    
                    # Update load point data
                    system['loads'].loc[LP, 'Lambda'] += system['sections']['Components'][sec][comp]['lambda']
                    system['loads'].loc[LP, 'U'] += system['sections']['Components'][sec][comp]['lambda'] * effectOnLPs[LP]
            print('LPs', effectOnLPs)
    # Print and save results
    system['loads']['R'] = system['loads']['U'] / system['loads']['Lambda']
    system['loads']['SAIFI'] = system['loads']['Lambda'] * system['loads']['Number of customers']
    system['loads']['SAIDI'] = system['loads']['U'] * system['loads']['Number of customers']
    system['loads']['CAIDI'] = system['loads']['R'] * system['loads']['Number of customers']
    system['loads']['EENS'] = system['loads']['U'] * system['loads']['Load level average [MW]']

    system['loads'].at['TOTAL', 'Number of customers'] = system['loads']['Number of customers'].sum()
    system['loads'].at['TOTAL', 'Load level average [MW]'] = system['loads']['Load level average [MW]'].sum()
    system['loads'].at['TOTAL', 'Load point peak [MW]'] = system['loads']['Load point peak [MW]'].sum()
    system['loads'].at['TOTAL', 'SAIFI'] = system['loads']['SAIFI'].sum() / (system['loads'].at['TOTAL', 'Number of customers'])
    system['loads'].at['TOTAL', 'SAIDI'] = system['loads']['SAIDI'].sum() / (system['loads'].at['TOTAL', 'Number of customers'])
    system['loads'].at['TOTAL', 'CAIDI'] = system['loads'].at['TOTAL', 'SAIDI'] / system['loads'].at['TOTAL', 'SAIFI']
    system['loads'].at['TOTAL', 'EENS'] = system['loads']['EENS'].sum()
    # Print and save results        
    system['loads'].to_excel(outFile, sheet_name='Load Points')
    if createFIM:
        FIM.to_excel(outFile, sheet_name='FIM')