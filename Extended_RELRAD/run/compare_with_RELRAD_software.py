import numpy as np
import pandas as pd
import warnings

warnings.filterwarnings("ignore", category=FutureWarning)
pd.options.mode.chained_assignment = None

import RELRAD_software.RELRAD as rr # RELRAD software
from Extended_RELRAD.run.run_case_studies import run_case_study
from Extended_RELRAD.case_studies.CINELDI_case_studies.Case_Study_II_multiple_RC import Case_Study_II_system
from Extended_RELRAD.case_studies.RBTS_Bus_2_case_studies.Bus_2_Case_A import Bus_2_Case_A_system
from Extended_RELRAD.case_studies.RBTS_Bus_2_case_studies.Bus_2_Case_D import Bus_2_Case_D_system

'''
Copyright (C) 2026 Jørgen Bratvold.

Part of a GPLv3-licensed thesis implementation derived in part from
RELRAD-software by Sondre Modalsli Aaberg.

Licensed under the GNU General Public License v3.0 or later.
See LICENSE for details.
'''

# Compare results from RELRAD 1.0 and RELRAD-software-new for the CINELDI system with three reserve connection with unlimited capacity

system_ENS_CINELDI_old, load_point_df = rr.RELRAD(
    "RELRAD_software/Test_Systems_Verified/CINELDI.xlsx",
    "RELRAD_software/RELRAD_software_results/CINELDI_results.xlsx",
    DERS=False, createFIM=False, DSEBF=False)

CINELDI_Base_all = [("Base-All", [1, 36, 62, 88], None, None, {}, False)]
details_CINELDI, _ = run_case_study(Case_Study_II_system, CINELDI_Base_all)
system_ENS_CINELDI_new = details_CINELDI["Base-All"]["total_ENS"]
load_point_ENS_CINELDI_new = pd.Series(details_CINELDI["Base-All"]["ENS_per_bus"]).to_numpy(dtype=float)
load_point_ENS_CINELDI_old = load_point_df.drop("TOTAL").to_numpy(dtype=float)

assert np.isclose(system_ENS_CINELDI_old, system_ENS_CINELDI_new, rtol=1e-6, atol=1e-9)
assert np.allclose(load_point_ENS_CINELDI_old, load_point_ENS_CINELDI_new, rtol=1e-6, atol=1e-9)

print(f"System ENS matches: {system_ENS_CINELDI_new:.6f} MWh/year")
print("Load point ENS matches.")



# Compare results from RELRAD 1.0 and RELRAD-software-new for the RBTS Bus 2 system Case A
system_ENS_RBTS_Bus_2_old, load_point_df = rr.RELRAD(
    "RELRAD_software/Test_Systems_Verified/BUS 2 Case A.xlsx",
    "RELRAD_software/RELRAD_software_results/RBTS_Bus_2_Case_A_results.xlsx",
    DERS=False, createFIM=False, DSEBF=False)

RBTS_Bus_2_Case_A = [("Base-A", [23, 28, 30, 34, 38], None, None, {}, False)]
details_RBTS_Bus_2_A, _ = run_case_study(Bus_2_Case_A_system, RBTS_Bus_2_Case_A)
system_ENS_RBTS_Bus_2_new = details_RBTS_Bus_2_A["Base-A"]["total_ENS"]

load_point_ENS_RBTS_Bus_2_new = pd.Series(details_RBTS_Bus_2_A["Base-A"]["ENS_per_bus"], dtype=float)

load_point_ENS_RBTS_Bus_2_new = load_point_ENS_RBTS_Bus_2_new[
    load_point_ENS_RBTS_Bus_2_new != 0
].to_numpy(dtype=float)

load_point_ENS_RBTS_Bus_2_old = load_point_df.drop("TOTAL").to_numpy(dtype=float)

assert np.isclose(system_ENS_RBTS_Bus_2_old, system_ENS_RBTS_Bus_2_new, rtol=1e-6, atol=1e-9)
assert np.allclose(load_point_ENS_RBTS_Bus_2_old, load_point_ENS_RBTS_Bus_2_new, rtol=1e-6, atol=1e-9)

print(f"System ENS matches: {system_ENS_RBTS_Bus_2_new:.6f} MWh/year")
print("Load point ENS matches")


# Compare results from RELRAD 1.0 and RELRAD-software-new for the RBTS Bus 2 system Case D
system_ENS_RBTS_Bus_2_old_D, load_point_df_D = rr.RELRAD(
    "RELRAD_software/Test_Systems_Verified/BUS 2 Case D.xlsx",
    "RELRAD_software/RELRAD_software_results/RBTS_Bus_2_Case_D_results.xlsx",
    DERS=False, createFIM=False, DSEBF=False)


RBTS_Bus_2_Case_D = [("Base-D", [23, 28, 30, 34, 38], None, None, {}, False)]
details_RBTS_Bus_2_D, _ = run_case_study(Bus_2_Case_D_system, RBTS_Bus_2_Case_D)

system_ENS_RBTS_Bus_2_new_D = details_RBTS_Bus_2_D["Base-D"]["total_ENS"]

load_point_ENS_RBTS_Bus_2_new_D = pd.Series(
    details_RBTS_Bus_2_D["Base-D"]["ENS_per_bus"], dtype=float
)

load_point_ENS_RBTS_Bus_2_new_D = load_point_ENS_RBTS_Bus_2_new_D[
    load_point_ENS_RBTS_Bus_2_new_D != 0
].to_numpy(dtype=float)

load_point_ENS_RBTS_Bus_2_old_D = load_point_df_D.drop("TOTAL").to_numpy(dtype=float)

assert np.isclose(system_ENS_RBTS_Bus_2_old_D, system_ENS_RBTS_Bus_2_new_D, rtol=1e-6, atol=1e-9)
assert np.allclose(load_point_ENS_RBTS_Bus_2_old_D, load_point_ENS_RBTS_Bus_2_new_D, rtol=1e-6, atol=1e-9)

print(f"System ENS matches for Case D: {system_ENS_RBTS_Bus_2_new_D:.6f} MWh/year")
print("Load point ENS matches for Case D")

