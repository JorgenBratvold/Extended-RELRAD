import numpy as np
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

def distributedGeneration(loads, generationData, connection, r, s):
    """
    Calculates the outage duration considering local distributed generation resources.
    
    Args:
        loads (DataFrame): Load point data including peak and average power demands
        generationData (DataFrame): Generation sources data including power limits and energy capacity
        connection (list): List of connected nodes (loads and generators)
        r (float): Total repair time in hours
        s (float): Switching time in hours
    
    Returns:
        float: Updated outage duration after considering distributed generation
    """
    # Initialize power and energy variables
    powerAvailable = 0    # Total power available from generators
    energyStorage = 0     # Total energy storage capacity
    powerNeeded = 0       # Total peak power demand
    energyNeeded = 0      # Total energy demand during outage

    # Calculate available resources and needed power/energy
    for i in connection:
        if i in generationData.index:
            # Handle generators without storage
            if generationData['Lim MW'][i] > 0 and generationData['E cap'][i] == 0:
                powerAvailable += generationData['Lim MW'][i]
                energyNeeded -= generationData['Lim MW'][i] * (r-s)  # Subtract constant generation
            # Handle generators with storage
            elif generationData['Lim MW'][i] > 0 and generationData['E cap'][i] > 0:
                energyStorage += generationData['E cap'][i]
                powerAvailable += generationData['Lim MW'][i]
        # Calculate load requirements
        if i in loads.index:
            powerNeeded += loads['Load point peak [MW]'][i]
            energyNeeded += loads['Load level average [MW]'][i] * (r-s)

    # Determine outage duration based on available resources
    if energyStorage > energyNeeded and powerAvailable > powerNeeded:
        return s  # Only switching time if enough power and energy available
    else:
        if powerAvailable > powerNeeded and energyNeeded > 0:
            # Calculate partial outage duration based on energy storage ratio
            u = (r-s) - (r-s)*(energyStorage/energyNeeded)
            return min(r, u+s)
        else:
            return r  # Full outage duration if insufficient resources

def loadCurveDistributedGeneration(energyNeeded, powerNeeded, generationData, connection, r, s):
    """
    Calculates outage duration using load curve data and distributed generation.
    
    Args:
        energyNeeded (float): Total energy demand during outage [MWh]
        powerNeeded (float): Peak power demand [MW]
        generationData (DataFrame): Generation sources data
        connection (list): List of connected nodes
        r (float): Repair time [hours]
        s (float): Switching time [hours]
    
    Returns:
        float: Updated outage duration considering load curve and DG
    """
    powerAvailable = 0
    energyStorage = 0
    energyNeeded = 0
    for i in connection:
        if i in generationData.index:
            if generationData['Lim MW'][i] > 0 and generationData['E cap'][i] == 0:
                powerAvailable += generationData['Lim MW'][i]
                powerNeeded -= generationData['Lim MW'][i] * (r-s)
            elif generationData['Lim MW'][i] > 0 and generationData['E cap'][i] > 0:
                energyStorage += generationData['E cap'][i]
                powerAvailable += generationData['Lim MW'][i]


    if energyStorage > energyNeeded and powerAvailable > powerNeeded:
        return s
    else:
        if powerAvailable > powerNeeded and energyNeeded > 0:
            u = (r-s) - (r-s)*(energyStorage/energyNeeded)
            return min(r, u+s)
        else:
            return r




def distributedGenerationNoPeak(loads, generationData, connection, r, s):
    """
    Calculates outage duration without considering peak power constraints.
    Only considers energy constraints from storage systems.
    """
    energyStorage = 0
    energyNeeded = 0
    for i in connection:
        if i in generationData.index:
            if generationData['Lim MW'][i] > 0 and generationData['E cap'][i] == 0:
                energyNeeded -= generationData['Lim MW'][i] * (r-s)
            elif generationData['Lim MW'][i] > 0 and generationData['E cap'][i] > 0:
                energyStorage += generationData['E cap'][i]
        if i in loads.index:
            energyNeeded += loads['Load level average [MW]'][i] * (r-s)

    if energyStorage > energyNeeded:
        return s
    else:
        u = (r-s) - (r-s)*(energyStorage/energyNeeded)
        return min(r, u+s)




def loadCurveDistributedGenerationNoPeak(energyNeeded, generationData, connection, r, s):
    """
    Calculates outage duration using load curve data without considering peak power constraints.
    
    Args:
        energyNeeded (float): Total energy demand during outage [MWh]
        generationData (DataFrame): Generation sources data
        connection (list): List of connected nodes
        r (float): Repair time [hours]
        s (float): Switching time [hours]
    
    Returns:
        float: Updated outage duration considering load curve and energy constraints
    """
    energyStorage = 0
    energyNeeded = 0
    for i in connection:
        if i in generationData.index:
            if generationData['Lim MW'][i] > 0 and generationData['E cap'][i] == 0:
                energyNeeded -= generationData['Lim MW'][i] * (r-s)
            elif generationData['Lim MW'][i] > 0 and generationData['E cap'][i] > 0:
                energyStorage += generationData['E cap'][i]


    if energyNeeded <= 0:
        return s
    if energyStorage > energyNeeded:
        return s
    else:
        u = (r-s) - (r-s)*(energyStorage/energyNeeded)
        return min(r, u+s)







def PV(t, Pr, R_c, G_std, G_max, LDI):
    """
    Simulates photovoltaic (PV) power production based on time and environmental factors.
    Implementation based on Enevoldsen2021.
    
    Args:
        t (float): Time in hours
        Pr (float): Rated power of PV system [MW]
        R_c (float): Critical radiation level
        G_std (float): Standard radiation level
        G_max (float): Maximum radiation level
        LDI (list): Monthly light distribution index
    
    Returns:
        float: PV power production [MW]
    """
    # Calculate temporal parameters
    month = t/(8736*30)  # Convert time to months (8736 hours/year)
    day = (month - np.floor(month)) * 30
    hour = (day - np.floor(day)) * 24

    # Adjust hour calculation for edge cases
    if hour == 0 or np.round(hour) == 0:
        hour = 24
    
    # Round temporal parameters
    month = np.ceil(month)
    day = np.ceil(day)
    hour = np.ceil(hour) if (hour-np.floor(hour)) >= 0.0001 else np.round(hour)

    # Calculate solar radiation based on time of day
    f = rng.uniform(0, 1)  # Random factor for radiation variation
    if hour >= 6 and hour < 18:  # Daylight hours
        # Parabolic radiation curve during day
        G_d = G_max*((-1/36*hour)**2 + 2/(3*hour) - 3)
        G = (G_d + f)*LDI[month]  # Apply monthly light distribution
    else:
        G = 0  # No radiation at night

    # Calculate PV production based on radiation level
    if G >= 0 and G < R_c:
        production_PV = Pr * G**2/(G_std * R_c)
    elif G >= R_c and G <= G_std:
        production_PV = Pr * G/G_std
    else:
        production_PV = Pr

    return production_PV

# todo: Implement wind power (WP) generation function
#def WP():

# todo: Implement battery energy storage system (BESS) function
#def BESS():
