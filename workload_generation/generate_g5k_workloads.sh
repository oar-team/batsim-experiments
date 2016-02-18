#!/usr/bin/bash

for platform_size in 34 37
do
    for random_seed in {0..4}
    do
        python json_workload_generator.py -i 4 ../job_calibration/workload_all_sizes_seq_calibrated.json "generated_workloads/g5k_workload_msg_seed${random_seed}_size${platform_size}.json" ${platform_size} -jn 250 -lambda 20 -k 20 -mu 0.25 -sigma 0.5 -rs ${random_seed}
        cp "generated_workloads/g5k_workload_msg_seed${random_seed}_size${platform_size}.json" ../simulated_experiment/workloads
    done
done
