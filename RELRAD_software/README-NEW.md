# RELRAD Software - Verified Systems

The verified systems related to this project are located in the folder:
Test_Systems_Verified

All verified results are included in the folder:
Verified_Results

To run the systems, go to Main.py.
All simulations are placed under the comment: ######## New Simulations ########  
It may be useful to comment out some lines, especially the MCS simulations, which take a long time when using a small beta value.

For more detailed instructions on running the code, refer to README.md.

In Main.py, an analysis and plotting function has also been added, which can be used to plot the bar charts shown in the report. These functions read data directly from the result files after running the system.

Example for RBTS Bus 2:

compare_manual_results(
    relrad_path="Verified_Results/RBTS_Bus_2/RELRAD_Results_Bus2_Case_E.xlsx",
    mcs_path="Verified_Results/RBTS_Bus_2/MC_Results_Bus2_Case_E.xlsx",
    mcs_loadcurve_path="Verified_Results/RBTS_Bus_2/MC_LC_Results_Bus2_Case_E.xlsx",
    reference_values=[0.248, 0.77, 3.08, 8.844],
    title="Reliability Indices Comparison – RBTS Bus 2 Case E",
    save_folder="Verified_Results/RBTS_Bus_2",
    save_fig=True
)

Here, relrad_path is the file path to the RELRAD solver results for the selected case.
mcs_path is the file path to the Monte Carlo Simulation results.
mcs_loadcurve_path points to the MCS results that include load curve modelling.
reference_values contains the benchmark reliability indices used for comparison (SAIFI, SAIDI, CAIDI, ENS).
title specifies the title of the generated comparison plot.
save_folder defines where the figure will be stored.
save_fig determines whether the plot is saved (True) or only displayed (False).





