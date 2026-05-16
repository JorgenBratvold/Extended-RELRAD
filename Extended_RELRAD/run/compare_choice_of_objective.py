
import pandas as pd
import numpy as np
from concurrent.futures import ProcessPoolExecutor, as_completed

# CINELDI case studies
from Extended_RELRAD.case_studies.CINELDI_case_studies.Case_Study_I_single_RC import Case_Study_I_system, Case_Study_I_cases
from Extended_RELRAD.case_studies.CINELDI_case_studies.Case_Study_II_multiple_RC import Case_Study_II_system, Case_Study_II_cases
from Extended_RELRAD.case_studies.CINELDI_case_studies.Case_Study_III_single_RC_BESS import Case_Study_III_system, Case_Study_III_cases
from Extended_RELRAD.case_studies.CINELDI_case_studies.Case_Study_IV_multiple_RC_BESS import Case_Study_IV_system, Case_Study_IV_cases
from Extended_RELRAD.case_studies.CINELDI_case_studies.Case_Study_V_single_RC_BESS_island import Case_Study_V_system, Case_Study_V_cases

from Extended_RELRAD.run.run_case_studies import run_case_study

def _run_one_CINELDI_job(args):
    study, system, cases, obj = args
    details, _ = run_case_study(system, cases, plot=False, objective=obj)
    return study, obj, {case: d["total_ENS"] for case, d in details.items()}


def run_all_CINELDI_objectives_parallel(
    out="Extended_RELRAD/case_studies_results/CINELDI_objectives.csv",
    max_workers=None,
):
    studies = {
        "I":   (Case_Study_I_system,   Case_Study_I_cases),
        "II":  (Case_Study_II_system,  Case_Study_II_cases),
        "III": (Case_Study_III_system, Case_Study_III_cases),
        "IV":  (Case_Study_IV_system,  Case_Study_IV_cases),
        "V":   (Case_Study_V_system,   Case_Study_V_cases),
    }

    jobs = [
        (study, system, cases, obj)
        for study, (system, cases) in studies.items()
        for obj in ["cost", "load_shed"]
    ]

    tmp = {}
    with ProcessPoolExecutor(max_workers=max_workers) as ex:
        for fut in as_completed([ex.submit(_run_one_CINELDI_job, j) for j in jobs]):
            study, obj, res = fut.result()
            for case, ens in res.items():
                tmp.setdefault((study, case), {})[obj] = ens

    rows = []
    for (study, case), v in tmp.items():
        cost = v.get("cost", np.nan)
        shed = v.get("load_shed", np.nan)
        rows.append({
            "study": study,
            "case": case,
            "ENS_cost": cost,
            "ENS_load_shed": shed,
            "pct_change_load_shed_vs_cost": 100 * (shed - cost) / cost if cost else np.nan,
        })

    df = pd.DataFrame(rows).sort_values(["study", "case"])
    df.to_csv(out, index=False)
    return df


if __name__ == "__main__":
    df = run_all_CINELDI_objectives_parallel(max_workers=10)
    print(df)