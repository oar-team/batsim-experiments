#!/usr/bin/bash

output_dir='generated_workloads/2016-04-26'

mkdir -p ${output_dir}

for platform_size in 32
do
    for random_seed in {0..9}
    do
        python json_workload_generator.py -i 4 profiles/delay_profiles_mpi_commands.json \
            "${output_dir}/g5k_micro_workload_delay_seed${random_seed}_size${platform_size}.json" ${platform_size} \
            -jn 700 -lambda 16 -k 4 -mu 0.25 -sigma 0.5 -rs ${random_seed} --maximum_job_length 600

        cp "${output_dir}/g5k_micro_workload_delay_seed${random_seed}_size${platform_size}.json" ../simulated_experiment/workloads
    done
done
