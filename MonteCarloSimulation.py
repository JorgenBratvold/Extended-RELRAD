import pandas as pd
import numpy as np
import random as rng
import GraphSearch as gs
import MiscFunctions as mf
import CreateSystem as cs
import EffectOfFault as ef
import VarianceCalculations as vc
import LoadCurve as lc
import LoadCurveEffectOfFault as lcef
import copy
import matplotlib.pyplot as plt
from concurrent.futures import ThreadPoolExecutor
from threading import Lock



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


def MonteCarlo(loc, outFile, beta = 0.05, nCap = 0, DSEBF = True, DERS = False, LoadCurve = False, DERScurve = False):
    lock = Lock()
    # Load data from Excel files and create the system
    system = cs.createSystem(loc, LoadCurve=LoadCurve)
    
    h = 8736  # Total hours in a year (52 weeks * 7 days * 24 hours)

    if LoadCurve: # Create load curve if load curve data is provided
        loadCurve = lc.createLoadCurve(system['loadCurveData'])
    else:
        loadCurve = False

    if DERS and DERScurve: # Create a randomly generated Generation curve as an example (for doing this properly, a separate curve should be created for each (type of) DER)
        DERScurve = lc.randomGenerationCurve()
    
    #print(loadCurve)
    # Perform Monte Carlo simulation for 600 years to find variance of EENS (multithreaded)
    if nCap > 0:
        n1 = max(nCap, 600)
    else:
        n1 = 600


    EENS = []


    testingU = []
    testingF = [] 


    if LoadCurve:
        ENS = 0
        # Perform Monte Carlo simulation for n years (multithreaded)
        with ThreadPoolExecutor() as executor:
            futures = [executor.submit(LoadCurveMonteCarloYear, system['sections'], system['buses'], system['loads'], system['generationData'], system['backupFeeders'], loadCurve, DERScurve, DSEBF=DSEBF, DERS = DERS) for year in range(n1)]
            with lock:
                for future in futures:
                    results, yearlyENS = future.result()
                    ENS += yearlyENS
                    EENS.append(yearlyENS)
                    for i in system['loads'].index:
                        system['loads'].at[i, 'nrOfFaults'] += results[i]['nrOfFaults']
                        system['loads'].at[i,'U'] += results[i]['U']

    else:
        # Perform Monte Carlo simulation for n years (multithreaded)
        with ThreadPoolExecutor() as executor:
            futures = [executor.submit(MonteCarloYear, system['sections'], system['buses'], system['loads'], system['generationData'], system['backupFeeders'], loadCurve, DSEBF=DSEBF, DERS = DERS) for year in range(n1)]
            with lock:
                for future in futures:
                    yearlyEENS = 0
                    results = future.result()
                    for LP in results:
                        yearlyEENS += results[LP]['U'] * system['loads'].at[LP, 'Load level average [MW]']
                    EENS.append(yearlyEENS)
                    for i in system['loads'].index:
                        system['loads'].at[i, 'nrOfFaults'] += results[i]['nrOfFaults']
                        system['loads'].at[i,'U'] += results[i]['U']

    EENS = np.array(EENS)

    
    n2 = vc.calcNumberOfSimulations(EENS, beta)  # Calculate number of simulations needed for desired variance

    #n2 = int(np.ceil(float(n2)*1.25))  # Increase number of simulations to 1.25 times the calculated value to compensate for inaccuracy in variance calculation (optional, should not be nessecary)
    
    if nCap > 0 and n2 > nCap: #Caps the number of simulations to nCap
        n2 = nCap

    n2 = max(0, n2 - n1) # Subtracts the already performed simulations from the total number of simulations needed

    
    if n2 > 0:
        if LoadCurve:
        # Perform Monte Carlo simulation for n years (multithreaded)
            with ThreadPoolExecutor() as executor:
                futures = [executor.submit(LoadCurveMonteCarloYear, system['sections'], system['buses'], system['loads'], system['generationData'], system['backupFeeders'], loadCurve, DERScurve, DSEBF=DSEBF) for year in range(n2)]
                with lock:
                    for future in futures:
                        results, yearlyENS = future.result()
                        ENS += yearlyENS
                        EENS = np.append(EENS, yearlyENS)
                        for i in system['loads'].index:
                            system['loads'].at[i,'nrOfFaults'] += results[i]['nrOfFaults']
                            system['loads'].at[i,'U'] += results[i]['U']

        else:
        # Perform Monte Carlo simulation for n years (multithreaded)
            with ThreadPoolExecutor() as executor:
                futures = [executor.submit(MonteCarloYear, system['sections'], system['buses'], system['loads'], system['generationData'], system['backupFeeders'], loadCurve, DSEBF=DSEBF) for year in range(n2)]
                with lock:
                    for future in futures:
                        yearlyEENS = 0
                        results = future.result()
                        for LP in results:
                            yearlyEENS += results[LP]['U'] * system['loads'].at[LP, 'Load level average [MW]']
                        EENS = np.append(EENS, yearlyEENS)
                        for i in system['loads'].index:
                            system['loads'].at[i, 'nrOfFaults'] += results[i]['nrOfFaults']
                            system['loads'].at[i,'U'] += results[i]['U']
    
    trueBeta = vc.calcBeta(EENS)  # Calculate the beta value for the EENS values


    if LoadCurve:
        for LP in system['loads'].index:
            system['loads'].at[LP, 'Lambda'] = system['loads'].at[LP, 'nrOfFaults'] / (n2+n1)
            system['loads'].at[LP, 'U']/= (n2+n1)
        
        system['loads']['R'] = system['loads']['U'] / system['loads']['Lambda']
        system['loads']['SAIFI'] = system['loads']['Lambda'] * system['loads']['Number of customers']
        system['loads']['SAIDI'] = system['loads']['U'] * system['loads']['Number of customers']
        system['loads']['CAIDI'] = system['loads']['R'] * system['loads']['Number of customers']
        #system['loads']['EENS'] = system['loads']['ENS'] / (n1 + n2)

        system['loads'].at['TOTAL', 'Number of customers'] = system['loads']['Number of customers'].sum()
        system['loads'].at['TOTAL', 'Load level average [MW]'] = system['loads']['Load point peak [MW]'].sum()*sum(loadCurve)/h
        system['loads'].at['TOTAL', 'Load point peak [MW]'] = system['loads']['Load point peak [MW]'].max()*max(loadCurve)
        system['loads'].at['TOTAL', 'SAIFI'] = system['loads']['SAIFI'].sum() / (system['loads'].at['TOTAL', 'Number of customers'])
        system['loads'].at['TOTAL', 'SAIDI'] = system['loads']['SAIDI'].sum() / (system['loads'].at['TOTAL', 'Number of customers'])
        system['loads'].at['TOTAL', 'CAIDI'] = system['loads'].at['TOTAL', 'SAIDI'] / system['loads'].at['TOTAL', 'SAIFI']
        system['loads'].at['TOTAL', 'EENS'] = ENS / (n1 + n2)
        system['loads'].at['TOTAL', 'nr of simulations'] = n1 + n2
        system['loads'].at['TOTAL', 'provided beta'] = beta
        system['loads'].at['TOTAL', 'calculated beta'] = trueBeta
        CI = vc.calcConfidenceInterval(EENS)  # Calculate the confidence interval for the EENS values
        system['loads'].at['TOTAL', 'EENS 95% CI'] = str(CI['CI95'])
        system['loads'].at['TOTAL', 'EENS 99% CI'] = str(CI['CI99'])



    else:
        # Calculate average failure rate and unavailability for each load point
        for LP in system['loads'].index:
            system['loads'].at[LP, 'Lambda'] = system['loads'].at[LP, 'nrOfFaults'] / (n2+n1)
            system['loads'].at[LP, 'U']/= (n2+n1)

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
        system['loads'].at['TOTAL', 'nr of simulations'] = n1 + n2
        system['loads'].at['TOTAL', 'provided beta'] = beta
        system['loads'].at['TOTAL', 'calculated beta'] = trueBeta
        CI = vc.calcConfidenceInterval(EENS)  # Calculate the confidence interval for the EENS values
        system['loads'].at['TOTAL', 'EENS 95% CI'] = str(CI['CI95'])
        system['loads'].at['TOTAL', 'EENS 99% CI'] = str(CI['CI99'])
        # Print and save results        
    
    system['loads'].to_excel(outFile, sheet_name='Load Points')



def GenerateHistory (l, r):
    TTF = (-1/l) * np.log(rng.uniform(0,0.999)) * 8736
    TTR = -r * np.log(rng.uniform(0,0.999))
    return TTF, TTR


def minTTF(history):
    TTFcomponent = next(iter(history))
    TTF = history[TTFcomponent]['TTF']
    for secComp in history:
        if history[secComp]['TTF'] < TTF:
            TTFcomponent = secComp
            TTF = history[secComp]['TTF']
    return TTFcomponent


def overlappingFaults(fault, history): #testing function (can be neglected)
    # Check if the fault overlaps with any other faults in the history
    for secComp in history:
        if secComp != fault:
            if (history[secComp]['TTF'] < history[fault]['TTF'] + history[fault]['TTR']) and (history[secComp]['TTF'] + history[secComp]['TTR'] > history[fault]['TTF']):
                return True
    return False


def MonteCarloYear(sectionsOriginal, busesOriginal, loads, generationData, backupFeeders, loadCurve, DSEBF=True, DERS = False):
    h = 8736  # Total hours in a year
    faultHistory = [] #testing variable for intermediate results
    results = {}
    for i in loads.index:
        results[i] = {'nrOfFaults': 0, 'U': 0}
    history = {}
        # Generate failure history for each component
    for sec in sectionsOriginal.index:
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
    #overlap = 0 #test vaiable to test for overlapping faults
    while history[fault]['TTF'] < h:
        faultHistory.append({'fault': fault, 'TTF': history[fault]['TTF'], 'TTR': history[fault]['TTR'], 'sec': history[fault]['sec'], 'comp': history[fault]['comp']}) #testing variable to store the fault history
        #count if there is an overlapping fault
        #if overlappingFaults(fault, history):
            #overlap += 1
        # Create deep copies of the original data for analysis
        sectionsCopy = pd.DataFrame(columns=sectionsOriginal.columns,
                                    data=copy.deepcopy(sectionsOriginal.values),
                                    index=sectionsOriginal.index)
        busesCopy = pd.DataFrame(columns=busesOriginal.columns,
                                    data=copy.deepcopy(busesOriginal.values),
                                    index=busesOriginal.index)
            
        # Makes sure the calculation does not go into the next year    
        if history[fault]['TTF'] + history[fault]['TTR'] > h:
            history[fault]['TTR'] = h - history[fault]['TTF']
        # Calculate the effects of faults on load points
        effectOnLPs = ef.faultEffects(history[fault]['sec'], history[fault]['comp'], busesCopy, sectionsCopy, loads, generationData, backupFeeders, history[fault]['TTR'], loadCurve=loadCurve, DSEBF=DSEBF, DERS = DERS)
            
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
    #if overlap > 0:
        #print('overlap', overlap)
    return results


def LoadCurveMonteCarloYear(sectionsOriginal, busesOriginal, loads, generationData, backupFeeders, loadCurve, DERScurve, DSEBF=True, DERS = False):
    h = 8736  # Total hours in a year
    results = {}
    totalENS = 0
    for i in loads.index:
        results[i] = {'nrOfFaults': 0, 'U': 0}
    history = {}
        # Generate failure history for each component
    for sec in sectionsOriginal.index:
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
        #print(fault)
            # Create deep copies of the original data for analysis
        sectionsCopy = pd.DataFrame(columns=sectionsOriginal.columns,
                                    data=copy.deepcopy(sectionsOriginal.values),
                                    index=sectionsOriginal.index)
        busesCopy = pd.DataFrame(columns=busesOriginal.columns,
                                    data=copy.deepcopy(busesOriginal.values),
                                    index=busesOriginal.index)
            
        # Makes sure the calculation does not go into the next year    
        if history[fault]['TTF'] + history[fault]['TTR'] > h:
            history[fault]['TTR'] = h - history[fault]['TTF']
        # Calculate the effects of faults on load points
        effectOnLPs, ENS = lcef.loadCurveFaultEffects(history[fault]['sec'], history[fault]['comp'], busesCopy, sectionsCopy, loads, generationData, backupFeeders, history[fault]['TTF'], history[fault]['TTR'], loadCurve=loadCurve, DERScurve=DERScurve, DSEBF=DSEBF, DERS = DERS)

        totalENS += ENS    
        for LP in effectOnLPs:
            if effectOnLPs[LP] > 0:
                # Update load point data
                results[LP]['nrOfFaults'] += 1
                results[LP]['U'] += effectOnLPs[LP]
                #results[LP]['ENS'] += effectOnLPs[LP]['ENS']

        # Generate new failure history for the faulted component
        newTTF, newTTR = GenerateHistory(history[fault]['l'], history[fault]['r'])

        history[fault]['TTF'] += newTTF + history[fault]['TTR']
        history[fault]['TTR'] = newTTR
        fault = minTTF(history)
    return results, totalENS