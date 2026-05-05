import numpy as np

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


def var(EENS):

    """
    calculates the varinace in EENS
    arguments:
        EENS: list of EENS values for each year
    returns:
        var: variance of EENS values
    """

    meanEENS = np.mean(EENS)

    var = np.sum((EENS-meanEENS)**2)/(len(EENS)-1)
    return var

def calcNumberOfSimulations(EENS, beta):
    # Calculate the number of simulations needed to achieve the desired precision

    meanEENS = np.mean(EENS)
    varEENS = var(EENS)


    n = ( np.sqrt(varEENS) / (beta * meanEENS)) ** 2
    n = int(np.ceil(n))

    return n

def calcBeta(EENS):
    #calculates the beta value for the EENS values
    meanEENS = np.mean(EENS)
    varEENS = var(EENS)
    beta = np.sqrt(varEENS) / (meanEENS * np.sqrt(len(EENS)))
    return beta
   
def calculate_iterations(confidence_level, std_dev, margin_of_error):
    """
    Calculate the number of Monte Carlo iterations required for a given confidence interval.

    Args:
        confidence_level (float): Desired confidence level (e.g., 0.95 for 95% confidence).
        std_dev (float): Standard deviation of the output metric.
        margin_of_error (float): Acceptable margin of error.

    Returns:
        int: Number of iterations required.
    """
    # Z-scores for common confidence levels
    z_scores = {0.90: 1.645, 0.95: 1.96, 0.99: 2.576}
    Z = z_scores[confidence_level]
    
    # Calculate the required number of iterations
    n = (Z * std_dev / margin_of_error) ** 2
    return np.ceil(n)

def calcConfidenceInterval(EENS):
    """
    Calculate the confidence interval for the EENS values.

    Args:
        EENS (list): List of EENS values.

    Returns:
        tuple: Lower and upper bounds of the confidence interval.
    """
    meanEENS = np.mean(EENS)  # Sample mean
    stdEENS = var(EENS)  # Sample standard deviation
    n = len(EENS) # Sample size
    
    return {'CI95':(meanEENS - (1.96 * (np.sqrt(stdEENS) / np.sqrt(n))), meanEENS + (1.96 * (np.sqrt(stdEENS) / np.sqrt(n)))), 
            'CI99':(meanEENS - (2.576 * (np.sqrt(stdEENS) / np.sqrt(n))), meanEENS + (2.576 * (np.sqrt(stdEENS) / np.sqrt(n))))}