#!/usr/bin/bash -e

rebuild_script="../workload_generation/generate_batsim_workload_from_oar_result.py"
output_dir="workloads"

mkdir -p ${output_dir}

for platform_size in 34 37
do
    for random_seed in {0..4}
    do
        oar_result_dir="../replay_workload/results_2016-02-17--21-35-37"
        if [ ${platform_size} -eq 37 ]
        then
            oar_result_dir="../replay_workload/results_2016-02-17--21-35-19"
            if [ ${random_seed} -eq 3 ]
            then
                # This execution is not taken into account because one job acted strangely in it
                # The job is batsim_job_id = 0, oar_job_id = 283 and took 1726 s instead of 1176.938262
                continue
            fi
        fi

        ${rebuild_script} -i4 -r "${oar_result_dir}/oar_gant_g5k_workload_delay${random_seed}.json.details" "${output_dir}/delay_seed${random_seed}_size${platform_size}.json"
    done
done
