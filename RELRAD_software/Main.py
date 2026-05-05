import pandas as pd
import RELRAD_software.MonteCarloSimulation as mc
import RELRAD_software.RELRAD as rr
import copy
from concurrent.futures import ThreadPoolExecutor

import os
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

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


# Main file, run either mc.MonteCarlo or rr.RELRAD here



#Examples:

#rr.RELRAD('RBMC p214.xlsx', 'RELRADResultsRBMCp214.xlsx')
#rr.RELRAD('Myhre 6Bus System.xlsx', 'RELRADResultsMyhre6Bus.xlsx', DSEBF = False, DERS = False)
#mc.MonteCarlo('Myhre 6Bus System.xlsx', 'MonteCarloResultsMyhre6Bus.xlsx', beta=0.02, DSEBF = False, LoadCurve=False, DERS=False)

#mc.MonteCarlo('BUS 2.xlsx', 'MonteCarloResultsBUS2.xlsx', beta=0.05, DSEBF = False)
#rr.RELRAD('BUS 2.xlsx', 'RELRADResultsBUS2.xlsx', DSEBF = False, createFIM=True, DERS=False)

'''
mc.MonteCarlo('BUS 4.xlsx', 'MonteCarloResultsBUS4.xlsx', beta=0.02, DSEBF = False)
rr.RELRAD('BUS 4.xlsx', 'RELRADResultsBUS4.xlsx', DSEBF = False)
mc.MonteCarlo('RBMC p214.xlsx', 'MonteCarloResultsRBMCp214.xlsx', beta=0.02, DSEBF = False)
rr.RELRAD('RBMC p214.xlsx', 'RELRADResultsRBMCp214.xlsx', DSEBF = False)
mc.MonteCarlo('BUS 2.xlsx', 'MonteCarloResultsBUS2.xlsx', beta=0.02, DSEBF = False)
rr.RELRAD('BUS 2.xlsx', 'RELRADResultsBUS2.xlsx', DSEBF = False)
mc.MonteCarlo('BUS 6.xlsx', 'MonteCarloResultsBUS6.xlsx', beta=0.02, DSEBF = False)
rr.RELRAD('BUS 6.xlsx', 'RELRADResultsBUS6.xlsx', DSEBF = False)
mc.MonteCarlo('SimpleTest.xlsx', 'MonteCarloResultsSimpleTest.xlsx', beta=0.02, DSEBF = False, DERS=False)
rr.RELRAD('SimpleTest.xlsx', 'RELRADResultsSimpleTest.xlsx', DSEBF = False, DERS=False)
'''

#mc.MonteCarlo('BUS 6 Sub2 mod.xlsx', 'MonteCarloResultsBUS6Sub2M.xlsx', beta=0.02, DSEBF = False, LoadCurve=False, DERS=False)
#mc.MonteCarlo('BUS 6 Sub2 mod.xlsx', 'MonteCarloResultsBUS6Sub2MLoadCurve.xlsx', beta=0.02, DSEBF = False, LoadCurve=True, DERS=False)
#mc.MonteCarlo('BUS 6 Sub2 mod.xlsx', 'MonteCarloResultsBUS6Sub2MDERS.xlsx', beta=0.02, DSEBF = False, LoadCurve=False, DERS=True)
#mc.MonteCarlo('BUS 6 Sub2 mod.xlsx', 'MonteCarloResultsBUS6Sub2MLoadCurveDERS.xlsx', beta=0.02, DSEBF = False, LoadCurve=True, DERS=True)
#mc.MonteCarlo('BUS 6 Sub2 mod.xlsx', 'MonteCarloResultsBUS6Sub2MDERSCurve.xlsx', beta=0.02, DSEBF = False, LoadCurve=True, DERScurve=True, DERS=True)


#rr.RELRAD('RBMC p214.xlsx', 'RELRADResultsRBMCp214DERS_BESS.xlsx', DSEBF = False, DERS = True)
#rr.RELRAD('RBMC p214.xlsx', 'RELRADResultsRBMCp214_DERSCase3.xlsx', DSEBF = False, DERS = True)


#mc.MonteCarlo('RBMC p214.xlsx', 'MonteCarloResults_p214_BaseCase.xlsx', beta=0.02, DSEBF = False, LoadCurve=False, DERS=False)
#mc.MonteCarlo('RBMC p214.xlsx', 'MonteCarloResults_p214_LoadCurve.xlsx', beta=0.02, DSEBF = False, LoadCurve=True, DERS=False)
#mc.MonteCarlo('RBMC p214.xlsx', 'MonteCarloResults_p214_DERS.xlsx', beta=0.02, DSEBF = False, LoadCurve=False, DERS=True)
#mc.MonteCarlo('RBMC p214.xlsx', 'MonteCarloResults_p214_LoadCurveDERS.xlsx', beta=0.02, DSEBF = False, LoadCurve=True, DERS=True)
#mc.MonteCarlo('RBMC p214.xlsx', 'MonteCarloResults_p214_DERSCurve.xlsx', beta=0.02, DSEBF = False, LoadCurve=True, DERScurve=True, DERS=True)

#rr.RELRAD('RBMC p214.xlsx', 'RELRADResultsRBMCp214.xlsx', DSEBF = False, DERS = False)
#rr.RELRAD('RBMC p214.xlsx', 'RELRADResultsRBMCp214DERS.xlsx', DSEBF = False, DERS = True)


#rr.RELRAD('BUS 6.xlsx', 'RELRADResultsBUS6.xlsx', DSEBF = False)



#rr.RELRAD('BUS 5 RELSAD MOD.xlsx', 'RELRADResultsBUS5.xlsx', DSEBF = False, DERS=False)
#mc.MonteCarlo('BUS 5 RELSAD MOD.xlsx', 'MonteCarloResultsBUS5.xlsx', beta=0.05, DSEBF = False, LoadCurve=False, DERS=False)


######## New Simulations ########

# BUS 2 case E
rr.RELRAD('Test_Systems_Verified/BUS 2 Case E.xlsx', 'Verified_Results/RBTS_Bus_2/RELRAD_Results_Bus2_Case_E.xlsx', DSEBF = False, DERS = False, createFIM=False)
mc.MonteCarlo('Test_Systems_Verified/BUS 2 Case E.xlsx', 'Verified_Results/RBTS_Bus_2/MC_LC_Results_Bus2_Case_E.xlsx', beta=0.02, DSEBF = False, LoadCurve=True, DERS=False)
mc.MonteCarlo('Test_Systems_Verified/BUS 2 Case E.xlsx', 'Verified_Results/RBTS_Bus_2/MC_Results_Bus2_Case_E.xlsx', beta=0.02, DSEBF = False, LoadCurve=False, DERS=False)

# BUS 4 case A
rr.RELRAD('Test_Systems_Verified/BUS 4 Case A.xlsx', 'Verified_Results/RBTS_Bus_4/RELRAD_Results_Bus4_Case_A.xlsx', DSEBF = False, DERS = False, createFIM=False)
mc.MonteCarlo('Test_Systems_Verified/BUS 4 Case A.xlsx', 'Verified_Results/RBTS_Bus_4/MC_LC_Results_Bus4_Case_A.xlsx', beta=0.02, DSEBF = False, LoadCurve=True, DERS=False)
mc.MonteCarlo('Test_Systems_Verified/BUS 4 Case A.xlsx', 'Verified_Results/RBTS_Bus_4/MC_Results_Bus4_Case_A.xlsx', beta=0.02, DSEBF = False, LoadCurve=False, DERS=False)


# BUS 6 
rr.RELRAD('Test_Systems_Verified/BUS 6_final.xlsx', 'Verified_Results/RBTS_Bus_6/RELRAD_Results_Bus6.xlsx', DSEBF = False, DERS = False, createFIM=False)
mc.MonteCarlo('Test_Systems_Verified/BUS 6_final.xlsx', 'Verified_Results/RBTS_Bus_6/MC_LC_Results_Bus6.xlsx', beta=0.02, DSEBF = False, LoadCurve=True, DERS=False)
mc.MonteCarlo('Test_Systems_Verified/BUS 6_final.xlsx', 'Verified_Results/RBTS_Bus_6/MC_Results_Bus6.xlsx', beta=0.02, DSEBF = False, LoadCurve=False, DERS=False)


# RBMC p214
rr.RELRAD('Test_Systems_Verified/RBMC p214.xlsx', 'Verified_Results/RBMC_p214/RELRAD_Results_RBMC_p214.xlsx', DSEBF = False, DERS = False, createFIM=False)
mc.MonteCarlo('Test_Systems_Verified/RBMC p214.xlsx', 'Verified_Results/RBMC_p214/MC_LC_Results_RBMC_p214.xlsx', beta=0.02, DSEBF = False, LoadCurve=True, DERS=False)
mc.MonteCarlo('Test_Systems_Verified/RBMC p214.xlsx', 'Verified_Results/RBMC_p214/MC_Results_RBMC_p214.xlsx', beta=0.02, DSEBF = False, LoadCurve=False, DERS=False)


# Simple test system
rr.RELRAD('Test_Systems_Verified/SimpleTest.xlsx', 'Verified_Results/Simple_Test/RELRAD_Results_SimpleTest.xlsx', DSEBF = False, DERS = False, createFIM=False)
mc.MonteCarlo('Test_Systems_Verified/SimpleTest.xlsx', 'Verified_Results/Simple_Test/MC_LC_Results_SimpleTest.xlsx', beta=0.02, DSEBF = False, LoadCurve=True, DERS=False)
mc.MonteCarlo('Test_Systems_Verified/SimpleTest.xlsx', 'Verified_Results/Simple_Test/MC_Results_SimpleTest.xlsx', beta=0.02, DSEBF = False, LoadCurve=False, DERS=False)



# Myhre 6Bus System
rr.RELRAD('Test_Systems_Verified/Myhre 6Bus System.xlsx', 'Verified_Results/Myhre_6bus/RELRAD_Results_Myhre6Bus.xlsx', DSEBF = False, DERS = False, createFIM=False)
mc.MonteCarlo('Test_Systems_Verified/Myhre 6Bus System.xlsx', 'Verified_Results/Myhre_6bus/MC_LC_Results_Myhre6Bus.xlsx', beta=0.02, DSEBF = False, LoadCurve=True, DERS=False)
mc.MonteCarlo('Test_Systems_Verified/Myhre 6Bus System.xlsx', 'Verified_Results/Myhre_6bus/MC_Results_Myhre6Bus.xlsx', beta=0.02, DSEBF = False, LoadCurve=False, DERS=False)


# Bus 2 case D (for comparison)
#rr.RELRAD('Test_Systems_Verified/BUS 2 Case D.xlsx', 'Verified_Results/RBTS_Bus_2/RELRAD_Results_Bus2_Case_D.xlsx', DSEBF = False, DERS = False, createFIM=False)


def compare_manual_results(
    relrad_path,
    mcs_path,
    mcs_loadcurve_path,
    reference_values=[0.248, 0.77, 3.08, 8.844],
    reference_values_MCS=None,   
    title="Reliability Indices Comparison – RBMC p214",
    save_folder="Verified_Results",
    save_fig=True
):
 

    def safe_read_excel(path):
        if not os.path.exists(path):
            print(f"File not found: {path}")
            return None
        return pd.read_excel(path, sheet_name="Load Points", index_col=0)

    # Read data
    relrad_df = safe_read_excel(relrad_path)
    mcs_df = safe_read_excel(mcs_path)
    mcs_loadcurve_df = safe_read_excel(mcs_loadcurve_path)

    relrad_total = relrad_df.loc['TOTAL', ['SAIFI', 'SAIDI', 'CAIDI', 'EENS']].astype(float).values
    mcs_total = mcs_df.loc['TOTAL', ['SAIFI', 'SAIDI', 'CAIDI', 'EENS']].astype(float).values if mcs_df is not None else [np.nan]*4
    mcs_loadcurve_total = mcs_loadcurve_df.loc['TOTAL', ['SAIFI', 'SAIDI', 'CAIDI', 'EENS']].astype(float).values if mcs_loadcurve_df is not None else [np.nan]*4

    # Extract info for legend
    def extract_info(df):
        if df is None:
            return None, None
        n_sim, beta = None, None
        for c in df.columns:
            lc = c.lower().strip()
            if "nr" in lc and "simul" in lc:
                val = df[c].dropna()
                if not val.empty:
                    n_sim = val.iloc[-1]
            elif "beta" in lc:
                val = df[c].dropna()
                if not val.empty:
                    beta = val.iloc[-1]
        return n_sim, beta

    mcs_n, mcs_beta = extract_info(mcs_df)
    mcs_lc_n, mcs_lc_beta = extract_info(mcs_loadcurve_df)

    # percentage difference calculation
    def diff(vals, refs):
        diffs = []
        for v, ref in zip(vals, refs):
            if ref == "no reference" or ref is None:
                diffs.append(np.nan)
            else:
                try:
                    diffs.append((v / ref - 1) * 100 if ref != 0 else np.nan)
                except Exception:
                    diffs.append(np.nan)
        return diffs

    relrad_diff = diff(relrad_total, reference_values)
    mcs_diff = diff(mcs_total, reference_values)
    mcs_loadcurve_diff = diff(mcs_loadcurve_total, reference_values)

    # If MCS reference is used
    if reference_values_MCS is not None:
        mcs_ref_diff = diff(mcs_total, reference_values_MCS)
        mcs_lc_ref_diff = diff(mcs_loadcurve_total, reference_values_MCS)
    else:
        mcs_ref_diff = None
        mcs_lc_ref_diff = None

    # Units
    units = {
        "SAIFI": r"$\frac{f.}{\mathrm{cust.}\cdot \mathrm{yr}}$",
        "SAIDI": r"$\frac{h}{\mathrm{cust.}\cdot \mathrm{yr}}$",
        "CAIDI": r"$\frac{h}{\mathrm{f.}}$",
        "EENS":  r"$\frac{\mathrm{MWh}}{\mathrm{yr}}$"
    }

    metrics = ['SAIFI', 'SAIDI', 'CAIDI', 'EENS']

    # Build dataset structure
    if reference_values_MCS is not None:
        datasets = {
            'Reference': reference_values,
            'Reference MCS': reference_values_MCS,
            'RELRAD': relrad_total,
            'MCS': mcs_total,
            'MCS (Load Curve)': mcs_loadcurve_total,
        }
        colors = {
            'Reference': 'lightgray',
            'Reference MCS': 'darkgray',
            'RELRAD': '#2E86C1',
            'MCS': '#28B463',
            'MCS (Load Curve)': '#F39C12',
        }
    else:
        datasets = {
            'Reference': reference_values,
            'RELRAD': relrad_total,
            'MCS': mcs_total,
            'MCS (Load Curve)': mcs_loadcurve_total,
        }
        colors = {
            'Reference': 'lightgray',
            'RELRAD': '#2E86C1',
            'MCS': '#28B463',
            'MCS (Load Curve)': '#F39C12',
        }

    # Plotting
    fig, axes = plt.subplots(2, 2, figsize=(12, 8))
    fig.subplots_adjust(wspace=0.30, hspace=0.20)

    axes = axes.flatten()
    width = 0.2

    for i, metric in enumerate(metrics):
        ax = axes[i]
        ref_val = reference_values[i]
        include_ref = not (ref_val == "no reference" or ref_val is None)

        current_datasets = datasets.copy()

        if not include_ref:
            current_datasets.pop('Reference', None)

        vals = [current_datasets[key][i] for key in current_datasets.keys()]
        bars = ax.bar(np.arange(len(current_datasets)), vals,
                      color=[colors[k] for k in current_datasets.keys()],
                      edgecolor='black', width=width*2.5)

        # Value annotation
        for j, bar in enumerate(bars):
            h = bar.get_height()
            if not np.isnan(h):
                ax.annotate(f'{h:.4f}', xy=(bar.get_x()+bar.get_width()/2, h),
                            xytext=(0, 4), textcoords="offset points",
                            ha='center', va='bottom', fontsize=9)

        if reference_values_MCS is None:
            diffs = [0] + [relrad_diff[i], mcs_diff[i], mcs_loadcurve_diff[i]]
        else:

            ref_mcs_diff = (reference_values_MCS[i] / reference_values[i] - 1) * 100

            diffs = [
                0,                        
                ref_mcs_diff,             
                relrad_diff[i],           
                mcs_ref_diff[i],          
                mcs_lc_ref_diff[i]        
            ]


        for j, diff_val in enumerate(diffs):
            if j < len(vals) and not np.isnan(diff_val) and j != 0:
                ax.text(j, vals[j] + (max(vals) * 0.10),
                        f'{diff_val:+.3f}%',
                        ha='center', va='bottom',
                        fontsize=9, fontweight='bold',
                        color=colors[list(current_datasets.keys())[j]])

        # Labels
        ax.set_title(f"{metric}", fontsize=11)
        ax.set_ylabel(f"{units[metric]}", fontsize=10)
        ax.set_xticks([])
        ax.grid(axis='y', linestyle='--', alpha=0.6)
        ax.set_ylim(0, max(vals)*1.25)

    
    legend_labels = list(datasets.keys())

    # Add N & beta to legend
    if mcs_n and mcs_beta and "MCS" in legend_labels:
        idx = legend_labels.index("MCS")
        legend_labels[idx] += f"\nN={int(mcs_n):,}\nβ={mcs_beta:.5f}"

    if mcs_lc_n and mcs_lc_beta and "MCS (Load Curve)" in legend_labels:
        idx = legend_labels.index("MCS (Load Curve)")
        legend_labels[idx] += f"\nN={int(mcs_lc_n):,}\nβ={mcs_lc_beta:.5f}"

    legend_colors = [colors[k] for k in datasets.keys()]
    legend_patches = [plt.Rectangle((0, 0), 1, 1, color=clr, ec='black') for clr in legend_colors]

    fig.legend(legend_patches, legend_labels,
               loc='lower center', bbox_to_anchor=(0.5, 0.01),
               ncol=len(legend_labels), fontsize=11, frameon=True)

    fig.suptitle(title, fontsize=14, fontweight='bold', y=0.99)

    if save_fig:
        save_name = os.path.join(save_folder, title.replace(" ", "_") + ".png")
        plt.savefig(save_name, dpi=300, bbox_inches='tight')
        print(f"Figure saved as: {save_name}")

    plt.show()


# Myhre 6Bus System
compare_manual_results(
    relrad_path="Verified_Results/Myhre_6bus/RELRAD_Results_Myhre6Bus.xlsx",
    mcs_path="Verified_Results/Myhre_6bus/MC_Results_Myhre6Bus.xlsx",
    mcs_loadcurve_path="Verified_Results/Myhre_6bus/MC_LC_Results_Myhre6Bus.xlsx",
    reference_values=[0.3500, 0.9395, 2.6842, 0.0178],  
    reference_values_MCS=[0.3441, 0.9409,  2.7365,  0.0174],
    title="Reliability Indices Comparison – Myhre 6Bus System",
    save_folder="Verified_Results/Myhre_6bus",
    save_fig=True
)


# Simple test system
compare_manual_results(
    relrad_path="Verified_Results/Simple_Test/RELRAD_Results_SimpleTest.xlsx",
    mcs_path="Verified_Results/Simple_Test/MC_Results_SimpleTest.xlsx",
    mcs_loadcurve_path="Verified_Results/Simple_Test/MC_LC_Results_SimpleTest.xlsx",
    reference_values=[2.2,  2.399,  1.090,  5.040],
    title="Reliability Indices Comparison – Simple Test System",
    save_folder="Verified_Results/Simple_Test",
    save_fig=True
)

# RBMC p214
compare_manual_results(
    relrad_path="Verified_Results/RBMC_p214/RELRAD_Results_RBMC_p214.xlsx",
    mcs_path="Verified_Results/RBMC_p214/MC_Results_RBMC_p214.xlsx",
    mcs_loadcurve_path="Verified_Results/RBMC_p214/MC_LC_Results_RBMC_p214.xlsx",
    reference_values=[1.23, 1.51, 1.23, "no reference"],
    title="Reliability Indices Comparison – RBMC p214",
    save_folder="Verified_Results/RBMC_p214",
    save_fig=True
)

# bus 2 case E
compare_manual_results(
    relrad_path="Verified_Results/RBTS_Bus_2/RELRAD_Results_Bus2_Case_E.xlsx",
    mcs_path="Verified_Results/RBTS_Bus_2/MC_Results_Bus2_Case_E.xlsx",
    mcs_loadcurve_path="Verified_Results/RBTS_Bus_2/MC_LC_Results_Bus2_Case_E.xlsx",
    reference_values=[0.248, 0.77, 3.08, 8.844],
    title="Reliability Indices Comparison – RBTS Bus 2 Case E",
    save_folder="Verified_Results/RBTS_Bus_2",
    save_fig=True
)

# bus 4 case A
compare_manual_results(
    relrad_path="Verified_Results/RBTS_Bus_4/RELRAD_Results_Bus4_Case_A.xlsx",
    mcs_path="Verified_Results/RBTS_Bus_4/MC_Results_Bus4_Case_A.xlsx",
    mcs_loadcurve_path="Verified_Results/RBTS_Bus_4/MC_LC_Results_Bus4_Case_A.xlsx",
    reference_values=[0.300, 3.47, 11.56, 54.293],
    title="Reliability Indices Comparison – RBTS Bus 4 Case A",
    save_folder="Verified_Results/RBTS_Bus_4",
    save_fig=True
)

# bus 6 
compare_manual_results(
    relrad_path="Verified_Results/RBTS_Bus_6/RELRAD_Results_Bus6.xlsx",
    mcs_path="Verified_Results/RBTS_Bus_6/MC_Results_Bus6.xlsx",
    mcs_loadcurve_path="Verified_Results/RBTS_Bus_6/MC_LC_Results_Bus6.xlsx",
    reference_values=[1.0067, 6.6688, 6.6247, 72.81531],
    title="Reliability Indices Comparison – RBTS Bus 6",
    save_folder="Verified_Results/RBTS_Bus_6",
    save_fig=True
)


