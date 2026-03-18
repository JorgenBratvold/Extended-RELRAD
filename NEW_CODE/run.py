import loadflow as lf
import CreateSystem as cs
import pandas as pd
import plotting as pl
import networkx as nx
import optimization as opt
import warnings
warnings.filterwarnings("ignore", category=FutureWarning)
warnings.filterwarnings("ignore", category=pd.errors.SettingWithCopyWarning)

if __name__ == "__main__":

    test_system = "NEW_CODE/new_systems/IEEE_123Bus.xlsx"
    #test_system = "NEW_CODE/new_systems/IEEE_123Bus_external_backfeeds.xlsx"
    #test_system = "NEW_CODE/new_systems/CINELDI.xlsx"

    Vbase = {'NEW_CODE/new_systems/IEEE_123Bus.xlsx': 4.16, 'NEW_CODE/new_systems/IEEE_123Bus_external_backfeeds.xlsx': 4.16, 'NEW_CODE/new_systems/CINELDI.xlsx': 22.0} # kV
    Sbase = {'NEW_CODE/new_systems/IEEE_123Bus.xlsx': 100, 'NEW_CODE/new_systems/IEEE_123Bus_external_backfeeds.xlsx': 100, 'NEW_CODE/new_systems/CINELDI.xlsx': 10000} # kVA
    
    pos = pl.load_positions(test_system)

    system = cs.createSystem(test_system, LoadCurve=False)
    buses_lf = pd.read_excel(test_system, sheet_name="Buses")
    lines_lf = pd.read_excel(test_system, sheet_name="Lines")

    fault = "S23"  # Example fault at bus S23

    # Baseline case
    lf.run_simulation(
        system,
        Sbase[test_system],
        Vbase[test_system],
        pos,
        buses_lf,
        lines_lf,
        system_name=test_system
    )

    # Fault case
    lf.run_simulation(
        system,
        Sbase[test_system],
        Vbase[test_system],
        pos,
        buses_lf,
        lines_lf,
        fault=fault,
        system_name=test_system
    )

    # Optimized case
    #system = cs.createSystem(test_system, LoadCurve=False)
    opt.run_simulation_optimized(
        system,
        Sbase[test_system],
        Vbase[test_system],
        pos,
        buses_lf,
        lines_lf,
        fault=fault,
        system_name=test_system,
        Vmin=0.95,
        Vmax=1.05
    )

