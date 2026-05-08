import time
import pandas as pd
from statistics import mean, stdev

from Extended_RELRAD.run.run_case_studies import run_case_study

'''
Copyright (C) 2026 Jørgen Bratvold.

Part of a GPLv3-licensed thesis implementation derived in part from
RELRAD-software by Sondre Modalsli Aaberg.

Licensed under the GNU General Public License v3.0 or later.
See LICENSE for details.
'''

def benchmark_case(system, cases, repeats=5, plot=False):
    times = []
    for _ in range(repeats):
        start = time.perf_counter()
        _, _ = run_case_study(system=system, cases=cases, plot=plot)
        times.append(time.perf_counter() - start)
    return {
        "runtime_mean_s": mean(times),
        "runtime_std_s": stdev(times) if len(times) > 1 else 0.0,
        "runs": repeats
    }

if __name__ == "__main__":
    results = []

    from Extended_RELRAD.case_studies.CINELDI_case_studies.Case_Study_I_single_RC import Case_Study_I_system
    CINELDI_single_RC_case = [("V095-Cap2-RC62", [1, 62], 0.95, 0.2, {}, False)]
    out = benchmark_case(Case_Study_I_system, CINELDI_single_RC_case, repeats=5, plot=False)
    results.append({"case": "V095-Cap2-RC62", **out})

    from Extended_RELRAD.case_studies.CINELDI_case_studies.Case_Study_II_multiple_RC import Case_Study_II_system
    CINELDI_multi_RC_case = [("V095-Cap2-All", [1, 36, 62, 88], 0.95, 0.2, {}, False)]
    out = benchmark_case(Case_Study_II_system, CINELDI_multi_RC_case, repeats=5, plot=False)
    results.append({"case": "V095-Cap2-All", **out})

    from Extended_RELRAD.case_studies.RBTS_Bus_2_case_studies.Bus_2_Case_A import Bus_2_Case_A_system
    RBTS_Bus_2_case_A_case = [("Cap2.0-A", [23, 28, 30, 34, 38], 0.0, 0.20, {}, False)]
    out = benchmark_case(Bus_2_Case_A_system, RBTS_Bus_2_case_A_case, repeats=5, plot=False)
    results.append({"case": "Cap2.0-A", **out})

    from Extended_RELRAD.case_studies.RBTS_Bus_2_case_studies.Bus_2_Case_D import Bus_2_Case_D_system
    RBTS_Bus_2_case_D_case = [("Cap2.0-D", [23, 28, 30, 34, 38], 0.0, 0.20, {}, False)]
    out = benchmark_case(Bus_2_Case_D_system, RBTS_Bus_2_case_D_case, repeats=5, plot=False)
    results.append({"case": "Cap2.0-D", **out})

    runtime_df = pd.DataFrame(results)
    print(runtime_df)