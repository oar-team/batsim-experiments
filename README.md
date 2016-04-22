# Batsim experiment repository

This project contains all the tools to experiment with Batsim. It was used
to produce experiment for the Batsim paper accepted at JSSPP 2016.

The different experiment parts are classified by folder:

* [scheduling_comparison](scheduling_comparison/README.md): Contains simple experiment made to compare
  different scheduling algorithm using Batsim.
* [replay_workload](replay_workload/README.md): Complete Batsim workload replay tool for OAR on Grid'5000
* simulated_experiment: Simulation experiment using Batsim
* [result_analysis](result_analysis/README.md): Analyse and compare OAR replay with simulation
* [workload_generation](workload_generation/README.md): Workload generation from real MPI jobs and generated worloads
* [noise_impact_experiment](noise_impact_experiment:/README.md) Some experiment about the noise (variation in
  decision and execution time) impact on scheduling
