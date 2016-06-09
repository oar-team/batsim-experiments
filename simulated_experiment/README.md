# Simulated experiment directory

This directory contains files related to the simulation-side of the experiments
done for JSSPP 2016.

The [launch_expe_config.py](simulated_experiment/launch_expe_config.py) script
is in charge of executing different simulations on different inputs, can compare
them with real (OAR) results and aggregate the different results.

The [config](simulated_experiment/config) directory contains input JSON files
for the [launch_expe_config.py](launch_expe_config.py) script.

The [platform](simulated_experiment/platform) directory contains the SimGrid
platforms used for our experiments.
