#!/usr/bin/bash

for i in {0..9}
do
    python json_workload_generator.py -i 4 profiles/delay_profiles_mpi_commands.json "generated_workloads/mini_workload${i}.json" 37 -jn 20 -lambda 1 -k 20 -mu 0.3 -sigma 0.5 -rs ${i}
done
