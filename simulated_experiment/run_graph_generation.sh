#!/usr/bin/bash -e

r_graph_generator='../result_analysis/compare_outputs.R'
r_aggregated_graph_generator='../result_analysis/analyse_aggregated.R'
oar_to_jobs_csv='../result_analysis/oar_result_to_batsim_csv.py'
check_calibration='../job_calibration/check_calibration_interferences.R'

real_dir34="../replay_workload/results_2016-02-17--21-35-37"
real_dir37="../replay_workload/results_2016-02-17--21-35-19"

aggregated_dir="simulated_run/aggregated"

mkdir -p ${aggregated_dir}

echo "submission_time_difference_mean,submission_time_difference_sd,execution_time_difference_mean,execution_time_difference_sd,waiting_time_difference_mean,waiting_time_difference_sd,turnaround_time_difference_mean,turnaround_time_difference_sd,stretch_difference_mean,stretch_difference_sd,makespan_difference,mean_stretch_difference,mean_waiting_time_difference,mean_turnaround_time_difference,workload_name,batsim_makespan,real_makespan,batsim_mean_stretch,real_mean_stretch,batsim_mean_waiting_time,real_mean_waiting_time,batsim_mean_turnaround_time,real_mean_turnaround_time" > ${aggregated_dir}/g5k_workload_delay_results.csv
echo "submission_time_difference_mean,submission_time_difference_sd,execution_time_difference_mean,execution_time_difference_sd,waiting_time_difference_mean,waiting_time_difference_sd,turnaround_time_difference_mean,turnaround_time_difference_sd,stretch_difference_mean,stretch_difference_sd,makespan_difference,mean_stretch_difference,mean_waiting_time_difference,mean_turnaround_time_difference,workload_name,batsim_makespan,real_makespan,batsim_mean_stretch,real_mean_stretch,batsim_mean_waiting_time,real_mean_waiting_time,batsim_mean_turnaround_time,real_mean_turnaround_time" > ${aggregated_dir}/g5k_workload_merged_msg_results.csv

for platform_size in 34 37
do
    for random_seed in {0..4}
    do
        for workload_name_prefix in 'g5k_workload_delay_' 'g5k_workload_merged_msg_'
        do
            if [ ${platform_size} -eq 37 ]
            then
                if [ ${random_seed} -eq 3 ]
                then
                    # This execution is not taken into account because one job acted strangely in it
                    # The job is batsim_job_id = 0, oar_job_id = 283 and took 1726 s instead of 1176.938262
                    # This job changes the whole schedule.
                    continue
                fi
            fi

            base_dir=$(pwd)
            cd "simulated_run/${workload_name_prefix}seed${random_seed}_size${platform_size}"
            graph_dir="graphs"
            mkdir -p ${graph_dir}

            echo "Generating graphs for platform_size=${platform_size}, random_seed=${random_seed}, workload_name_prefix=${workload_name_prefix}"

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

            batsim_jobs_out="output/${workload_name_prefix}seed${random_seed}_size${platform_size}_jobs.csv"
            oar_gant_out="${base_dir}/${real_dir}/oar_gant_g5k_workload_delay${random_seed}.json"
            oar_gant_out_detailed="${base_dir}/${real_dir}/oar_gant_g5k_workload_delay${random_seed}.json.details"
            batsim_jobs_csv="batsim_jobs.csv"
            real_jobs_csv="real_jobs.csv"
            mapping="${base_dir}/${real_dir}/g5k_workload_delay${random_seed}-job_id_mapping.csv"

            # Retrieve OAR gantt files
            cp ${oar_gant_out} oar_gantt.json
            cp ${oar_gant_out_detailed} oar_gantt_detailed.json

            # Retrieve OAR job id mapping
            cp ${mapping} job_id_mapping.csv

            # Retrieve batsim jobs csv output
            cp ${batsim_jobs_out} ${batsim_jobs_csv}

            # Retrieve real jobs csv output
            ${base_dir}/${oar_to_jobs_csv} -r -m ${mapping} ${oar_gant_out} ${real_jobs_csv} \
            >output/real_to_jobs_csv.stdout 2>output/real_to_jobs_csv.stderr

            # Generate graphs & check calibration
            Rscript --vanilla "${base_dir}/${r_graph_generator}" "${batsim_jobs_csv}" "${real_jobs_csv}" ${graph_dir} \
            ${workload_name_prefix}seed${random_seed}_size${platform_size} >output/graph_generation.stdout 2>output/graph_generation.stderr

            # Aggregage output
            cat ${graph_dir}/differences.csv | \
            sed 1d >> "${base_dir}/${aggregated_dir}/${workload_name_prefix}results.csv"

            cd ${base_dir}
        done
    done
done

Rscript --vanilla "${base_dir}/${r_aggregated_graph_generator}" "${aggregated_dir}/g5k_workload_delay_results.csv" \
"${aggregated_dir}/g5k_workload_merged_msg_results.csv" ${aggregated_dir} \
>graph_aggregated.stdout 2>graph_aggregated.stderr

exit 0
