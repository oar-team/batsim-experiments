#!/usr/bin/bash -e

if [ $# -lt 6 ]
then
    echo 'Expected parameters : BATSIM_EXECUTABLE BATAAR_EXECUTABLE SOURCE_WORKLOAD OAR_GANTT_JSON NB_WORKLOADS_TO_GENERATE EXPERIMENT_NAME [NO_NOISE]'
    exit 1
fi

# Reading args
batsim=$1
bataar=$2
source_workload=$3
oar_gantt_json=$4
nb_workloads_to_generate=$5
experiment_name=$6
no_noise=false

if [ $# -eq 7 ]
then
    echo "Noise is disabled"
    no_noise=true
fi

# Fixed links to other scripts
generate_noisy_workload_script="../workload_generation/create_noisy_workload.py"
generate_metrics_from_jobs="../result_analysis/analyse_schedule_jobs.R"
oar_to_jobs_csv='../result_analysis/oar_result_to_batsim_csv.py'
generate_aggregated_graphs="../result_analysis/do_metrics_graphs_aggregated.R"

# Creating variables
base_dir=$(pwd)
experiment_directory="${base_dir}/${experiment_name}"
generated_workloads_directory="${experiment_directory}/generated_workloads"
batsim_out_directory="${experiment_directory}/batsim_output"
stdout_directory="${experiment_directory}/stdout_and_err"
aggregated_directory="${experiment_directory}/aggregated"
out_metrics_dir="${experiment_directory}/metrics_output"
out_graphs_dir="${experiment_directory}/graphs"
aggregated_schedules="${aggregated_directory}/schedules.csv"


real_dir34="../replay_workload/results_2016-02-17--21-35-37"
real_dir37="../replay_workload/results_2016-02-17--21-35-19"

# Create directories
mkdir -p ${generated_workloads_directory}
mkdir -p ${batsim_out_directory}
mkdir -p ${stdout_directory}
mkdir -p ${aggregated_directory}
mkdir -p ${out_metrics_dir}
mkdir -p ${out_graphs_dir}

echo "Generating noisy workloads..."
for (( noise=0; noise<${nb_workloads_to_generate}; noise++ ))
do
    if [ ${no_noise} = true ]
    then
        python3 ${generate_noisy_workload_script} -i 4 --random_seed ${noise} ${source_workload} "${generated_workloads_directory}/noisy_workload${noise}.json" --runtime_noise_mu 0 --runtime_noise_sigma 1e-9 --subtime_noise_mu 0 --subtime_noise_sigma 1e-9
    else
        python3 ${generate_noisy_workload_script} -i 4 --random_seed ${noise} ${source_workload} "${generated_workloads_directory}/noisy_workload${noise}.json"
    fi
done

echo "Simulating workloads..."
for (( noise=0; noise<${nb_workloads_to_generate}; noise++ ))
do
    workload_name="noisy_workload${noise}"
    workload_filename="${generated_workloads_directory}/${workload_name}.json"

    echo "Simulating workload ${workload_name}"

    # Run batsim in the background
    ${batsim} -m'graphene-1144.nancy.grid5000.fr' ../simulated_experiment/platforms/graphene.xml \
    ${workload_filename} \
    -e "${batsim_out_directory}/${workload_name}" \
    > "${stdout_directory}/${workload_name}_batsim.stdout" 2>"${stdout_directory}/${workload_name}_batsim.stderr" & batsim_pid=$!

    # Wait few seconds then run bataar
    sleep 2
    ${bataar} ${workload_filename} \
    > "${stdout_directory}/${workload_name}_bataar.stdout" 2>"${stdout_directory}/${workload_name}_bataar.stderr" & bataar_pid=$!

    # Sync
    wait ${batsim_pid}
    wait ${bataar_pid}

    # Analyse the resulting Batsim's _jobs.csv to compute scheduling metrics
    Rscript --vanilla ${generate_metrics_from_jobs} "${batsim_out_directory}/${workload_name}_jobs.csv" "${out_metrics_dir}/${workload_name}_metrics.csv" "${workload_name}" "batsim"

done

echo "Aggregating results..."
# Let's obtain a _jobs.csv for the real execution of the workload
python3 ${oar_to_jobs_csv} -r "${oar_gantt_json}" "${batsim_out_directory}/real_jobs.csv" \
    > "${stdout_directory}/real_to_jobs_csv.stdout" 2>"${stdout_directory}/real_to_jobs_csv.stderr"

# Let's generate scheduling metrics from it
Rscript --vanilla ${generate_metrics_from_jobs} "${batsim_out_directory}/real_jobs.csv" "${out_metrics_dir}/real_metrics.csv" "real" "real"

# Let's create the aggregated file
cp -f "${out_metrics_dir}/real_metrics.csv" ${aggregated_schedules}
for (( noise=0; noise<${nb_workloads_to_generate}; noise++ ))
do
    workload_name="noisy_workload${noise}"
    cat "${out_metrics_dir}/${workload_name}_metrics.csv" | sed -n '2p' >> ${aggregated_schedules}
done

# Let's generate some graphs
echo "Generating graphs..."
Rscript --vanilla "${generate_aggregated_graphs}" "${aggregated_schedules}" "${out_graphs_dir}" \
    > "${stdout_directory}/graph_generation.stdout" 2> "${stdout_directory}/graph_generation.stderr"

exit 0
