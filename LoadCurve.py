import numpy as np
import pandas as pd
import random as rng

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

def createLoadCurve(loadCurveData):
    loadCurve = []
    for t in range(1, 8737):
        week = t/(8736/52)
        day = (week-np.floor(week))*7
        hour = (day-np.floor(day))*24

        if day == 0:
            day = 7

        if hour == 0 or round(hour) == 0:
            hour = 24
        
        # Rounding to the nearest upper integer
        week = int(np.ceil(week))
        day = int(np.ceil(day))
        if (hour-np.floor(hour)) < 0.0001:
            hour = int(np.round(hour))
        else:
            hour = int(np.ceil(hour))


        if day == 6 or day == 7: #weekend
            if week >= 1 and week <= 8: # Winter
                hourlyfactor = 'Winter Wknd'
            elif week >= 9 and week <= 17: # Spring
                hourlyfactor = 'Spring/Fall Wknd'
            elif week >= 18 and week <= 30: # Summer
                hourlyfactor = 'Summer Wknd'
            elif week >= 31 and week <= 43: # Fall
                hourlyfactor = 'Spring/Fall Wknd'
            else: # Winter
                hourlyfactor = 'Winter Wknd'
        
        else: # weekday
            if week >= 1 and week <= 8: # Winter
                hourlyfactor = 'Winter Wkdy'
            elif week >= 9 and week <= 17: # Spring
                hourlyfactor = 'Spring/Fall Wkdy'
            elif week >= 18 and week <= 30: # Summer
                hourlyfactor = 'Summer Wkdy'
            elif week >= 31 and week <= 43: # Fall
                hourlyfactor = 'Spring/Fall Wkdy'
            else: # Winter
                hourlyfactor = 'Winter Wkdy'
 
        loadCurve.append(loadCurveData['weeklyFactor'].at[week, 'Load Factor']/100 * loadCurveData['dailyFactor'].at[day, 'Load Factor']/100 * loadCurveData['hourlyFactor'].at[hour, hourlyfactor]/100) # (Factors are given in %.)
    loadCurve.append(0) #failure prevention
    loadCurve.append(0)
    return loadCurve



def loadCurveSumEnergy(t, r, loadList, loads, loadCurve):

    if r is None:
        return 0

    peakLoad = 0
    for load in loadList:
        peakLoad += loads['Load point peak [MW]'][load] # Peak load in MW

    E = 0
    
    #creates a list of the length of time the load is in each of the load curve points
    # The first element is the time from t to the next full hour, the last element is the time from the last full hour to r
    timeList = []
    timeList.append(min(1-t%1, r))
    for i in range(int(np.floor(r-min(1-t%1, r)))):
        timeList.append(1)
    timeList.append(min((r-(1-t%1))%1, (r-min(1-t%1, r))%1))


    for i in range(len(timeList)):
        timePoint = int(np.floor(t+i))
        if timePoint >= 8736:
            return E
        E += timeList[i] * loadCurve[timePoint] * peakLoad # Energy in MWh
        
    return E


def randomGenerationCurve():
    generationCurve = []
    for i in range(8738): # Flat generation curve, 1 for each hour of the year
        generationCurve.append(rng.uniform(0, 2))
    return generationCurve



    
def LCandDERScurve(t, r, s, loadList, loads, loadCurve, generationData, connection, generationCurve, storageCurve = None): 

    storageCurve = generationCurve.copy() #uses the generation curve = storage curve for simple example


    if r is None:
        return 0, 0
    

    peakLoad = 0
    for load in loadList:
        peakLoad += loads['Load point peak [MW]'][load] # Peak load in MW

    
    ENS = 0
    U = 0
    #Calculates the ammount of energy not served during switchig
    timeList = []
    timeList.append(min(1-t%1, s))
    for i in range(int(np.floor(s-min(1-t%1, s)))):
        timeList.append(1)
    timeList.append(min((s-(1-t%1))%1, (s-min(1-t%1, s))%1))

    for i in range(len(timeList)):
        timePoint = int(np.floor(t+i))
        if timePoint >= 8736:
            return ENS, U
        ENS += timeList[i] * loadCurve[timePoint] * peakLoad
        U += timeList[i]
    t += s
    r -= s


    localGeneration = 0
    energyStorage = 0
    storagePower = 0
    for i in connection:
        if i in generationData.index:
            if generationData['Lim MW'][i] > 0 and generationData['E cap'][i] == 0:
                localGeneration += generationData['Lim MW'][i]
            elif generationData['Lim MW'][i] > 0 and generationData['E cap'][i] > 0:
                energyStorage += generationData['E cap'][i]
                storagePower += generationData['Lim MW'][i]
    
    #creates a list of the length of time the load is in each of the load curve points
    # The first element is the time from t to the next full hour, the last element is the time from the last full hour to r
    timeList = []
    timeList.append(min(1-t%1, r))
    for i in range(int(np.floor(r-min(1-t%1, r)))):
        timeList.append(1)
    timeList.append(min((r-(1-t%1))%1, (r-min(1-t%1, r))%1))


    storage = storageCurve[int(np.floor(t-s))] * energyStorage


    for i in range(len(timeList)):
        timePoint = int(np.floor(t+i))
        if timePoint >= 8736:
            U = min(r, U)
            return ENS, U
        if generationCurve[timePoint] * localGeneration > loadCurve[timePoint] * peakLoad:
            ENS += 0 
            U += 0
            #print(1)
        elif generationCurve[timePoint] * localGeneration *timeList[i] + storage > loadCurve[timePoint] * peakLoad * timeList[i] and generationCurve[timePoint] * localGeneration + storagePower > loadCurve[timePoint] * peakLoad:
            storage -= loadCurve[timePoint] * peakLoad * timeList[i] - generationCurve[timePoint] * localGeneration * timeList[i]
            ENS += 0
            U += 0
            #print(2)
        elif generationCurve[timePoint] * localGeneration + storagePower > loadCurve[timePoint] * peakLoad and storage > 0:
            storage = 0
            ENS += loadCurve[timePoint] * peakLoad * timeList[i] - generationCurve[timePoint] * localGeneration * timeList[i] - storage
            U += timeList[i] - timeList[i] * storage / (loadCurve[timePoint] * peakLoad * timeList[i] - generationCurve[timePoint] * localGeneration * timeList[i])
            #print(3)
        else:
            ENS += timeList[i] * loadCurve[timePoint] * peakLoad
            U += timeList[i]
            #print(4)

    U = min(r, U)
    return ENS, U





def loadPeak(t, r, loadList, loads, loadCurve):
    if r is None:
        return 0

    peakLoad = 0
    for load in loadList:
        peakLoad += loads['Load point peak [MW]'][load] # Peak load in MW
    
    #creates a list of the length of time the load is in each of the load curve points
    # The first element is the time from t to the next full hour, the last element is the time from the last full hour to r
    timeList = []
    timeList.append(1-t%1)
    for i in range(int(np.floor(r-1+t%1))):
        timeList.append(1)
    timeList.append((r-(1-t%1))%1)

    P = 0
    for i in range(len(timeList)):
        timePoint = int(np.floor(t+i))
        if timePoint >= 8736:
            return P
        if loadCurve[timePoint] * peakLoad > P:
            P = loadCurve[timePoint] * peakLoad
    return P