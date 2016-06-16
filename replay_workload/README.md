# Replay workloads

This folder contains a tool that is made to replay a Batsim workload
on a real OAR cluster on Grid'5000.

It is heavily based on the [Execo](http://execo.gforge.inria.fr) library for
remote execution, Grid'5000 bindings and experiment parameter sweeping.

## Requirements

You need python2 and a modified version of Execo because of bug on parameters
overload.

So install python 2 and the pip installer and then install Execo like this.
```bash
pip2 install --user git+https://github.com/mickours/execo.git
```

## Usage

Just run the ``oar_replay_workload.py`` script to see the usage:
```bash
$ ./oar_replay_workload.py
Usage: <program> [options] <arguments>

engine: oar_replay_workload

Arguments:
  experiment_config: The config JSON experiment description file

Options:
  -h, --help            show this help message and exit
  -l LOG_LEVEL          log level (int or string). Default = inherit execo
                        logger level
  -L                    copy stdout / stderr to log files in the experiment
                        result directory. Default = False
  -R                    redirect stdout / stderr to log files in the
                        experiment result directory. Default = False
  -M                    when copying or redirecting outputs, merge stdout /
                        stderr in a single file. Default = False
  -c DIR                use experiment directory DIR
  --is_a_test           prefix the result folder with "test", enter a debug
                        mode if fails and remove the job afterward, unless it
                        is a reservation
  --already_configured  if set, the OAR cluster is not re-configured
  --reservation_id=RESERVATION_ID
                        Grid'5000 reservation job ID
```

To run an experiment, connect to a Grid'5000 frontal and run the script
with an experiment description file as parameter:
```bash
./oar_replay_workload.py my_experiment.json
```

If your experiment did not finished or crash you can rerun it using the same result directory so only the workloads that do not have been done are rerun. (It use the [``execo_engine`` module](http://execo.gforge.inria.fr/doc/latest-stable/execo_engine.html#module-execo_engine) for this):
```bash
./oar_replay_workload.py my_experiment.json -c results_directory
```

Here is an example of experiment description JSON file:
```javascript
{
  "description": "This experiment is running 10 workload on 32 nodes under a fixed switch (sgraphene1) for batsim comparison: First run",
  "grid5000_site": "Nancy",
  "resources": "{switch='sgraphene1'}/switch=1",
  "walltime": "08:00:00",
  "nb_experiment_nodes": 33,
  "kadeploy_env_name": "debian8_workload_generation_nfs",
  "workloads": [
    "/home/mmercier/expe-batsim/workload_generation/generated_workloads/2016-05-04/g5k_workload_delay_seed1_size32.json"
    "/home/mmercier/expe-batsim/workload_generation/generated_workloads/2016-05-04/g5k_workload_delay_seed2_size32.json"
  ]
}
```
