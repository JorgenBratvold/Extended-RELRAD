import numpy as np
import pandas as pd
import re 
from datetime import datetime
import matplotlib.pyplot as plt 

def load_pvgis_timeseries(path: str) -> pd.DataFrame:
    with open(path, "r", encoding="utf-8", errors="ignore") as f:
        lines = f.readlines()

    header_line = None
    for i, line in enumerate(lines):
        if line.strip().lower().startswith("time,"):
            header_line = i
            break
    if header_line is None:
        raise ValueError(f"Fant ikke 'time,'-header i {path}")

    df = pd.read_csv(path, skiprows=header_line, low_memory=False)

    time_pattern = re.compile(r"^\d{8}:\d{4}$") #
    df = df[df["time"].astype(str).str.match(time_pattern)].copy()

    df["time"] = pd.to_datetime(df["time"], format="%Y%m%d:%H%M")

    for c in ["Gb(i)", "Gd(i)", "Gr(i)"]:
        df[c] = pd.to_numeric(df[c], errors="coerce")

    df["G_total"] = df["Gb(i)"] + df["Gd(i)"] + df["Gr(i)"]
    df = df.dropna(subset=["G_total"]).sort_values("time").reset_index(drop=True)

    return df

def build_typical_year_8760(df: pd.DataFrame, years_to_use: int = None) -> np.ndarray:
    df = df.copy()
    df["year"] = df["time"].dt.year

    years = sorted(df["year"].unique())
    if years_to_use is not None and len(years) > years_to_use:
        years = years[-years_to_use:]
        df = df[df["year"].isin(years)].copy()

    df = df[~((df["time"].dt.month == 2) & (df["time"].dt.day == 29))].copy() 

    df["hour"] = df["time"].dt.hour
    df["doy_noleap"] = df["time"].apply(
        lambda t: datetime(2001, t.month, t.day).timetuple().tm_yday
    )

    typical = (
        df.groupby(["doy_noleap", "hour"])["G_total"]
          .mean()
          .reset_index()
          .sort_values(["doy_noleap", "hour"])
    )

    full_index = pd.MultiIndex.from_product(
        [range(1, 366), range(0, 24)],
        names=["doy_noleap", "hour"]
    )
    typical = (typical.set_index(["doy_noleap", "hour"])
                      .reindex(full_index)
                      .fillna(0.0)
                      .reset_index())

    curve = typical["G_total"].to_numpy()
    assert len(curve) == 8760
    return curve

def to_8736_from_8760(curve_8760: np.ndarray) -> np.ndarray:
    curve_8760 = np.asarray(curve_8760)
    if len(curve_8760) != 8760:
        raise ValueError(f"Forventer 8760, fikk {len(curve_8760)}")

    days = curve_8760.reshape(365, 24)
    daily_energy = days.sum(axis=1)


    remove_day = int(np.argmin(daily_energy))
    keep_mask = np.ones(365, dtype=bool)
    keep_mask[remove_day] = False

    curve_8736 = days[keep_mask].reshape(-1)
    assert len(curve_8736) == 8736
    return curve_8736

def PVproduction(G: np.ndarray, P_rated: float, G_std: float = 1000.0, R_c_Wm2: float = 150.0) -> np.ndarray:
    G = np.asarray(G)
    if np.max(G) <= 0:
        return np.zeros_like(G, dtype=float)

    g_pu = G / G_std
    r_c = R_c_Wm2 / G_std

    P_pu = np.zeros_like(g_pu, dtype=float)
    P_pu[g_pu < r_c] = (g_pu[g_pu < r_c] ** 2) / r_c
    mid = (g_pu >= r_c) & (g_pu <= 1.0)
    P_pu[mid] = g_pu[mid]
    P_pu[g_pu > 1.0] = 1.0

    return P_rated * P_pu


def build_representative_pv_power_8736(csv_path: str, P_rated: float, years_to_use: int = None,
                                       G_std: float = 1000.0, R_c_Wm2: float = 150.0) -> np.ndarray:
    df = load_pvgis_timeseries(csv_path)
    G_8760 = build_typical_year_8760(df, years_to_use=years_to_use)
    #G_8736 = to_8736_from_8760(G_8760)
    #P_8736 = PVproduction(G_8736, P_rated=P_rated, G_std=G_std, R_c_Wm2=R_c_Wm2)
    #convert to list
    #P_8736 = P_8736.tolist()
    #return P_8736
    P_8760 = PVproduction(G_8760, P_rated=P_rated, G_std=G_std, R_c_Wm2=R_c_Wm2)
    return P_8760


if __name__ == "__main__":
    CSV_TRD = "NEW_CODE/solar_timeseries_trondheim_2013_2023.csv"
    #CSV_MAD = "DG_models/PV_solar/solar_timeseries_madrid_2013_2023.csv"

    P_trd = build_representative_pv_power_8736(CSV_TRD, P_rated=1.0, years_to_use=10)
    #P_mad = build_representative_pv_power_8736(CSV_MAD, P_rated=1.0, years_to_use=10)


    plt.figure(figsize=(12, 5))
    #plt.plot(P_mad, label="Madrid", color="#0072B2")
    plt.plot(P_trd, label="Trondheim", color="#E69F00")

    plt.xlabel("Time [hours]")
    plt.ylabel("PV Power [p.u.]")
    plt.title("Representative 8736-hour PV Power Curve")
    plt.legend()
    plt.grid()
    plt.tight_layout()
    plt.show()
