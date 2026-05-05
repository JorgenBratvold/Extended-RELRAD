import pandas as pd

def build_network(excel_file, use_lambda_temp=False):
    """
    Builds the network data structure from the given Excel file.
    The Excel file should have two sheets: "Buses" and "Lines". The "Buses" sheet should contain the bus data, and the "Lines" sheet should contain the line data.

    Args:
        excel_file (str): Path to the Excel file containing the system data.
        use_lambda_temp (bool): Whether to include the temporary failure rate in the total failure rate calculation.
    
    Returns:
        dict: A dictionary containing the network data structure with keys "buses", "lines", "positions", "edge_lookup", and "upstream_lookup".  
    """
    
    buses_df = pd.read_excel(excel_file, "Buses")
    lines_df = pd.read_excel(excel_file, "Lines")

    network = {
        "buses": {},
        "lines": {},
        "positions": {},
        "edge_lookup": {},
        "upstream_lookup": {}
    }

    def f(row, col, default=0.0):
        return float(row[col]) if col in row.index and not pd.isna(row[col]) else default

    for _, row in buses_df.iterrows():
        bid = int(row["Bus"]) - 1

        network["buses"][bid] = {
            "P_load": f(row, "P [pu]"), # extra copy of active power load in pu
            "P": f(row, "P [pu]"),
            "Q": f(row, "Q [pu]"),
            "P_MW": f(row, "P [MW]"),
            "Q_MVAr": f(row, "Q [MVAr]"),
            "customers": int(row["Number_of_Customers"]) if not pd.isna(row["Number_of_Customers"]) else 0,
            "c1": f(row, "Cost_1h [NOK/kWh]"),
            "c4": f(row, "Cost_4h [NOK/kWh]"),
            "connected_lines": []
        }

        if not pd.isna(row["Bus_x_pos"]) and not pd.isna(row["Bus_y_pos"]):
            network["positions"][bid] = (f(row, "Bus_x_pos"), f(row, "Bus_y_pos"))

    for _, row in lines_df.iterrows():
        line_label = str(row["Line"]).strip()
        line_id = int(line_label.replace("L", "")) 

        up = int(row["From_Bus"]) - 1
        down = int(row["To_Bus"]) - 1

        disc = str(row["Disconnector_Direction"]).strip()
        breaker = str(row["Breaker_Direction"]).strip()

        if disc not in {"N", "U", "D", "B"}:
            raise ValueError(f"Invalid Disconnector_Direction '{disc}' for {line_label}")

        length = f(row, "Length [km]")

        lambda_base = f(row, "Failure_Rate [1/yr/km]") * length
        r_base = f(row, "Repair_Time [h]")

        lambda_temp = f(row, "Temporary_Failure_Rate [1/yr]") if use_lambda_temp else 0.0
        r_temp = f(row, "Temporary_Repair_Time [h]") if use_lambda_temp else 0.0

        lambda_transformer = f(row, "Transformer_Failure_Rate [1/yr]")
        r_transformer = f(row, "Transformer_Repair_Time [h]")

        lambda_total = lambda_base + lambda_temp + lambda_transformer

        repair_time = (
            lambda_base * r_base
            + lambda_temp * r_temp
            + lambda_transformer * r_transformer
        ) / lambda_total if lambda_total > 0 else 0.0

        network["lines"][line_id] = {
            "label": line_label,
            "up": up,
            "down": down,
            "r": f(row, "r [pu]"),
            "x": f(row, "x [pu]"),
            "b": f(row, "b [pu]"),
            "r_ohm": f(row, "r [ohm]"),
            "x_ohm": f(row, "x [ohm]"),
            "b_S": f(row, "b [S]"),
            "disc": disc,
            "breaker": breaker,
            "fault": False,
            "lambda": lambda_total,
            "repair_time": repair_time,
            "switch_time": f(row, "Switching_Time [h]"),
            "length": length
        }

        network["buses"][up]["connected_lines"].append(line_id)
        network["buses"][down]["connected_lines"].append(line_id)

    network["edge_lookup"] = {
        (u, v): line_id
        for line_id, line in network["lines"].items()
        for u, v in [(line["up"], line["down"]), (line["down"], line["up"])]
    }

    network["upstream_lookup"] = {
        line["down"]: line_id
        for line_id, line in network["lines"].items()
    }

    return network