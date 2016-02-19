#!/usr/bin/bash

for platform_size in 34 37
do
    for random_seed in {0..4}
    do
        python simulation_workload_generator.py -i 4 ../job_calibration/workload_all_sizes_seq_calibrated.json "generated_workloads/g5k_workload_delay${random_seed}.json" "generated_workloads/g5k_workload_merged_msg_seed${random_seed}_size${platform_size}.json" ${platform_size}
        cp "generated_workloads/g5k_workload_merged_msg_seed${random_seed}_size${platform_size}.json" ../simulated_experiment/workloads

        python simulation_workload_generator.py -i 4 "generated_workloads/g5k_workload_delay${random_seed}.json" "generated_workloads/g5k_workload_delay${random_seed}.json" "generated_workloads/g5k_workload_delay_seed${random_seed}_size${platform_size}.json" ${platform_size}
        cp "generated_workloads/g5k_workload_delay_seed${random_seed}_size${platform_size}.json" ../simulated_experiment/workloads
    done
done
