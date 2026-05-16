# Extended RELRAD: Reliability Assessment with Secure Post-Fault Restoration

## Description

This repository contains the Python implementation developed as part of the master's thesis:

**Reliability Assessment of Distribution Systems Including Operational Constraints & Branch-and-Bound Optimization for Post-Fault Restoration** 

The software extends the RELRAD framework by including operational constraints, currently supporting capacity limits on reserve connections (RCs) and lower voltage magnitude limits at buses, to ensure a secure operating state after restoration from a contingency. It includes scripts for running case studies, comparing results with the original RELRAD software and reference studies, comparing LinDistFlow with DALF and other existing solvers, visualizing the restored system state following contingencies, and analyzing computational efficiency.

## License and attribution

This repository contains two main code folders:

- `RELRAD_software/`: the original RELRAD-software source code by Sondre Modalsli Aaberg. The source code is unchanged, but some input system files have been slightly adapted for use in this thesis. 
- `Extended_RELRAD/`: the modified and extended thesis implementation developed by Jørgen Bratvold.

Selected parts of `Extended_RELRAD/` are adapted from `RELRAD_software`, originally licensed under the GNU General Public License v3.0 or later.

`Extended_RELRAD/` reorganizes and extends the original implementation with functionality for operational constraints, secure post-fault restoration, and branch-and-bound optimization.

This repository is distributed under the GNU General Public License v3.0 or later. See `LICENSE` for details.

## Repository structure

```text
.
├── Extended_RELRAD/                         # Thesis implementation
│   ├── case_studies/                        # Case study definitions
│   ├── case_studies_results/                # Pre-computed results and plots
│   ├── compatible_systems/                  # System input data
|   ├── contingency_plots/                   # Pre-computed contingency plots
│   ├── run/                                 # Scripts for analyses and comparisons
|   |   ├── compare_choice_of_objective.py
│   │   ├── compare_LF_solvers.py
│   │   ├── compare_with_RELRAD_software.py
│   │   ├── run_20_Bus_Test_Examples.py
│   │   ├── run_and_plot_single_contingencies.py
│   │   ├── run_case_studies.py
│   │   ├── run_computational_efficiency.py
│   │   └── run_original_RBTS_case_study.py
│   └── src/                                 # Main source code
│
├── RELRAD_software/                         # Original RELRAD software
├── LICENSE
└── README.md
```

## Requirements

The project requires Python 3.9 or newer.

Required Python packages:

- numpy
- pandas
- matplotlib
- openpyxl
- tqdm

## Supported systems

The following systems are currently supported. All listed systems include specified coordinates and can therefore be plotted.

| System | RC capacity limit | Voltage limit | Notes |
|---|:---:|:---:|---|
| RBTS Bus 2 | ✓ | Optional | Voltage-limit studies require assumed branch impedance data. |
| RBTS Bus 4 | ✓ | Optional | Voltage-limit studies require assumed branch impedance data. |
| CINELDI MV reference system | ✓ | ✓ | Supports both RC capacity and voltage-limit studies. |
| IEEE 123-Bus | ✓ | ✓ | Reliability data must be assumed. |
| 20 Bus Test System | ✓ | ✓ | Supports both RC capacity and voltage-limit studies. |


## Usage

Run all scripts from the repository root directory.

Main scripts, case setups, and system input data are located in:

```text
Extended_RELRAD/run/
Extended_RELRAD/case_studies/
Extended_RELRAD/compatible_systems/
```

Run the main thesis case studies with:

```bash
python Extended_RELRAD/run/run_case_studies.py
```

Additional scripts in `Extended_RELRAD/run/` are provided for solver comparisons, objective function sensitivity analysis, original RELRAD comparisons, contingency visualization, computational efficiency analysis, and 20-bus test examples.

Generated results and plots are saved in:

```text
Extended_RELRAD/case_studies_results/
Extended_RELRAD/contingency_plots/
```

## Notes and limitations

- Systems with multiple reserve connections that can be connected within the same area may produce unintuitive results. This is due to the current sequential switching logic, where reserve connections are evaluated and connected one at a time rather than optimized jointly.

- The code currently calculates ENS only. Additional reliability indices must be implemented separately if needed.

- If new systems are added and should be plotted, bus coordinates must be specified.

- The input Excel file structure used in this implementation differs from the structure used in the original RELRAD software.