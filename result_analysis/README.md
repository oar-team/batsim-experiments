# Results analysis directory

This directory contains data analysis scripts used for the experiments done for
JSSPP 2016.

## Scripts

The different scripts contain more information regarding what they do in their
respective headers. The different scripts are:

- [compare_outputs.R](compare_outputs.R): Compares two
  executions of the same workload on the same platform, one being real (OAR) and
  the one coming from Batsim. This script generates figures and creates a
  comparison summary into a differences.csv file.
- [analyse_schedule_jobs.R](analyse_schedule_jobs.R): This
  script analyses one single execution of a workload (a BATSIM _jobs.csv file)
  and exports different metrics into an output CSV file.
- [do_metrics_graphs_aggregated.R](do_metrics_graphs_aggregated.R):
  This script computes graphs from an aggregated result file. Such an aggregated
  result file can be obtained by combining different results from the
  [analyse_schedule_jobs.R](analyse_schedule_jobs.R) script.
- [oar_gantt_reader.py](oar_gantt_reader.py): This script reads an OAR gantt
  and displays some information about it. It was mainly used to check whether
  OAR results were consistent.
- [oar_result_to_batsim_csv.py](oar_result_to_batsim_csv.py): This script
  transforms an OAR gantt result file into a Batsim _jobs CSV file. It is used
  to compare simulated and real experiments by comparing the two _jobs CSV files.
