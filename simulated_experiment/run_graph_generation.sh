#!/usr/bin/bash -e

r_graph_generator='../result_analysis/compare_outputs.R'
oar_to_jobs_csv='../result_analysis/oar_result_to_batsim_csv.py'

real_dir34="../replay_workload/results_2016-02-17--21-35-37"
real_dir37="../replay_workload/results_2016-02-17--21-35-19"


for platform_size in 34 37
do
    for random_seed in {0..4}
    do
        base_dir=$(pwd)
        cd "simulated_run/g5k_workload_msg_seed${random_seed}_size${platform_size}"
        graph_dir="graphs"
        mkdir ${graph_dir}

        echo "Generating graphs for platform_size=${platform_size}, random_seed=${random_seed}"

        real_dir=""

        if [ ${platform_size} -eq 34 ]
        then
            real_dir=${real_dir34}
        elif [ ${platform_size} -eq 37 ]
        then
            real_dir=${real_dir37}
        else
            echo "Invalid platform_size: ${platform_size}"
            exit 1
        fi

        batsim_jobs_out="output/g5k_workload_msg_seed${random_seed}_size${platform_size}_jobs.csv"
        oar_gant_out="${base_dir}/${real_dir}/oar_gant_g5k_workload_delay${random_seed}.json"
        batsim_jobs_csv="batsim_jobs.csv"
        real_jobs_csv="real_jobs.csv"
        mapping="${base_dir}/${real_dir}/g5k_workload_delay${random_seed}-job_id_mapping.csv"

        # Retrieve batsim jobs csv output
        cp ${batsim_jobs_out} ${batsim_jobs_csv}

        # Retrieve real jobs csv output
        ${base_dir}/${oar_to_jobs_csv} -r -m ${mapping} ${oar_gant_out} ${real_jobs_csv}

        # Generate graphs
        Rscript --vanilla "${base_dir}/${r_graph_generator}" "${batsim_jobs_csv}" "${real_jobs_csv}" ${graph_dir}

        cd ${base_dir}
    done
done

exit 0
