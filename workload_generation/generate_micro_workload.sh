#!/usr/bin/bash

for i in {0..9}
do
    python json_workload_generator.py -i 4 profiles/delay_profiles_mpi_commands.json "generated_workloads/micro_workload${i}.json" 32 -jn 1 -lambda 1 -k 20 -mu 0 -sigma 0.5 -rs ${i}
done
