# Extended RELRAD: Reliability Assessment with Secure Post-Fault Restoration

## Description

This repository contains the Python implementation developed as part of the master's thesis:

**Reliability Assessment of Distribution Systems Including Operational Constraints & Branch-and-Bound Optimization for Post-Fault Restoration**

The software extends the RELRAD framework by including operational constraints, currently supporting capacity limits on reserve connections (RCs) and lower voltage magnitude limits at buses, to ensure a secure operating state after restoration from a contingency. It includes scripts for running case studies, comparing results with the original RELRAD software and reference studies, comparing LinDistFlow with DALF and other existing solvers, visualizing the restored system state following contingencies, and analyzing computational efficiency.

## Supported systems

The following systems are currently supported. All listed systems include specified coordinates and can therefore be plotted.

| System | RC capacity limit | Voltage limit | Notes |
|---|:---:|:---:|---|
| RBTS Bus 2 | ✓ | Optional | Voltage-limit studies require assumed branch impedance data. |
| RBTS Bus 4 | ✓ | Optional | Voltage-limit studies require assumed branch impedance data. |
| CINELDI MV reference system | ✓ | ✓ | Supports both RC capacity and voltage-limit studies. |
| IEEE 123-Bus | ✓ | ✓ | Reliability data must be assumed. |
| 20 Bus Test System | ✓ | ✓ | Supports both RC capacity and voltage-limit studies. |

## Repository structure 

```text

Extended_RELRAD/                              # All the code implemented in this thesis
├── case_studies/                             # Case study setups 
├── case_studies_results                      # Pre-computed case study results with plots
├── compatible_systems/                       # System input data used in case study setup
├── run/                                      # Scripts for case studies and comparisons
│   ├── compare_LF_solvers.py                 # Compares LinDistFlow and DALF
│   ├── compare_with_RELRAD_software.py       # Compares with original RELRAD software results
│   ├── run_20_Bus_Test_Examples.py           # Runs 20-bus test examples
│   ├── run_and_plot_single_contingencies.py  # Visualizes post-fault restoration state after switching
│   ├── run_case_studies.py                   # Runs thesis case studies
|   ├── run_computational_efficiency.py       # Runs efficiency analyses
│   └── run_original_RBTS_case_study.py       # Runs original case studies A-F on RBTS Bus 2 and 4
├── src/                                      # Main source code
└── README.md                                 # Project documentation

RELRAD_software/                              # Includes the code from the original RELRAD software
```

## Requirements

The project requires Python 3.9 or newer.

Required Python packages:

- numpy
- pandas
- matplotlib
- openpyxl
- tqdm

## Usage

Run all scripts from the repository root directory.

The main scripts are located in `Extended_RELRAD/run/`.

### Run the main thesis case studies

Run:

    python Extended_RELRAD/run/run_case_studies.py

This runs the main case studies defined in `Extended_RELRAD/case_studies/` and uses system input files from `Extended_RELRAD/compatible_systems/`.

### Compare with the original RELRAD software

Run:

    python Extended_RELRAD/run/Compare_with_RELRAD_software.py

This compares the new implementation with the original RELRAD software included in `RELRAD_software/`.

### Run the original RBTS cases A--F

Run:

    python Extended_RELRAD/run/run_original_RBTS_case_study.py

This runs the original RBTS Bus 2 and Bus 4 cases A--F from Allan et al. using the new implementation.

### Compare load-flow solvers

Run:

    python Extended_RELRAD/run/Compare_LF_solvers.py

This compares the LinDistFlow approximation with DALF.

### Visualize single contingencies

Run:

    python Extended_RELRAD/run/run_and_plot_single_contingencies.py

This visualizes the restored system state after selected contingencies and switching actions.

### Run computational efficiency analyses

Run:

    python Extended_RELRAD/run/run_computational_efficiency.py

This runs the computational efficiency analyses for the branch-and-bound restoration algorithm.

### Run 20-bus test examples

Run:

    python Extended_RELRAD/run/run_20_Bus_Test_Examples.py

This runs example contingencies for the 20 Bus Test System presented in the thesis.

### Output files

Generated results and plots are saved to `Extended_RELRAD/case_studies_results/`.


## Notes and limitations

- Systems with multiple reserve connections that can be connected within the same area may produce unintuitive results. This is due to the current sequential switching logic, where reserve connections are evaluated and connected one at a time rather than optimized jointly.

- The code currently calculates ENS only. Additional reliability indices must be implemented separately if needed.

- If new systems are added and should be plotted, bus coordinates must be specified.

- The input Excel file structure used in this implementation differs from the structure used in the original RELRAD software.