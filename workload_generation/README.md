# Workload generation directory

This directory contains scripts that are related to the generation
of workloads used for the Batsim paper accepted at JSSPP 2016.

## Subdirectories
The different subdirectories are:

* [generated_workload](generated_workload): The workloads that have been
  generated for the experiments are placed in this directory.
* [NPB_bin](NPB_bin): Contains the binary files we were able to compile from the
  NAS Parallel Benchmarks.
* [job_calibration](job_calibration): Contains file related to the calibration
  of the MSG profiles, to make their execution times match the ones on the
  Graphene cluster.
* [tit_to_profile_validation](tit_to_profile_validation): Contains a little
  MPI C++ example. This has been useful to create the script
  [tit2batprof.py](tit2batprof.py)

## Scripts
All (or almost all) scripts have their own help page, which can be shown just by
calling the script with the --help option. The different scripts in this folder
are:

* [json_workload_generator.py](json_workload_generator.py): The main script of
  this folder, in charge of generating a Batsim JSON workload input from a profile
  list. An input example of this script can be found in
  [profiles_example.json](profiles_example.json)
* Different wrapper scripts that call
  [json_workload_generator.py](json_workload_generator.py). They are used to store
  the parameters of the call.
  * [generate_g5k_workloads_2016-05-04.sh](generate_g5k_workloads_2016-05-04.sh)
  * [generate_g5k_workloads_2016-05-04_msg.sh](generate_g5k_workloads_2016-05-04_msg.sh)
  * [generate_micro_workload.sh](generate_micro_workload.sh)
  * [generate_mini_workload.sh](generate_mini_workload.sh)
  * [generate_mini_workload_msg.sh](generate_mini_workload_msg.sh)
* [generate_batsim_workload_from_oar_result.py](generate_batsim_workload_from_oar_result.py):
  This script allows to create a Batsim JSON input workload file from an OAR gantt
  JSON file. The resulting file will contain jobs with delay profiles.
* [translate_submission_times.py](translate_submission_times.py): This script
  modifies a Batsim JSON workload file. It translates the submission times of
  jobs such that the first submission will be done at time 0.
* [create_noisy_workload.py](create_noisy_workload.py): This script reads a
  Batsim workload file, adds some noise on the submission time and the execution
  time of jobs (according to some parameters), then writes the result in another
  Batsim workload file.
* [tit2batprof.py](tit2batprof.py): This script reads a SimGrid time-indepent
  trace (TIT) file which corresponds to a single job execution and transforms
  it into a Batsim profile, which is added into a Batsim profiles JSON file.
* [prv2tit.pl](prv2tit.pl): A script that transforms a PRV file to a SimGrid
  TIT file, courtesy of Lucas Schnorr. More information can be found on
  [his labbook](https://github.com/tcbozzetti/trabalhoconclusao/blob/master/LabBook.org).
* [mpi_bench.py](mpi_bench.py): This script generate the MPI traces using the
  NAS benchmarks and the Extrae tracing tool.
* [extract_tit_trace.sh](extract_tit_trace.sh) TODO
