#!/usr/bin/bash

for i in {0..9}
do
    python json_workload_generator.py -i 4 ../job_calibration/workload_all_sizes_seq_calibrated.json "generated_workloads/mini_workload_msg${i}.json" 35 -jn 20 -lambda 1 -k 20 -mu 0.3 -sigma 0.5 -rs ${i}
done
