#!/usr/bin/bash

for i in {0..5}
do
    python json_workload_generator.py -i 4 profiles/delay_profiles_mpi_commands.json "generated_workloads/g5k_workload_delay${i}.json" 37 -jn 250 -lambda 20 -k 20 -mu 0.25 -sigma 0.5 -rs ${i}
done
