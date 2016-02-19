#!/usr/bin/bash -e

if [ $# -ne 2 ]
then
    echo 'Expected parameters : BATSIM_EXECUTABLE BATAAR_EXECUTABLE'
    exit 1
fi

batsim=$1
bataar=$2

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
                    continue
                fi
            fi
            base_dir=$(pwd)
            mkdir -p "simulated_run/${workload_name_prefix}seed${random_seed}_size${platform_size}/output"
            cd "simulated_run/${workload_name_prefix}seed${random_seed}_size${platform_size}/output"

            echo "Running experiment random_seed=${random_seed}, platform_size=${platform_size}, workload_name_prefix=${workload_name_prefix}"

            # Run batsim in the background
            ${batsim} -m'graphene-1144.nancy.grid5000.fr' ${base_dir}/platforms/graphene.xml \
            "${base_dir}/workloads/${workload_name_prefix}seed${random_seed}_size${platform_size}.json" \
            -e "${workload_name_prefix}seed${random_seed}_size${platform_size}" \
            >batsim.stdout 2>batsim.stderr & batsim_pid=$!

            # Wait few seconds then run bataar
            sleep 2
            ${bataar} "${base_dir}/workloads/${workload_name_prefix}seed${random_seed}_size${platform_size}.json" \
            >bataar.stdout 2>bataar.stderr & bataar_pid=$!

            # Sync
            wait ${batsim_pid}
            wait ${bataar_pid}

            cd ${base_dir}
        done
    done
done

exit 0
