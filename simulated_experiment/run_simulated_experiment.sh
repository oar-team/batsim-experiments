#!/usr/bin/bash -e

if [ $# -ne 2 ]
then
    echo 'Expected parameters : BATSIM_EXECUTABLE SCHED_EXECUTABLE'
    exit 1
fi

batsim=$1
sched=$2

use_bataar=false

for platform_size in 32
do
    for random_seed in {0..9}
    do
        for workload_name_prefix in 'g5k_workload_delay_'
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

            echo "Running experiment platform_size=${platform_size}, random_seed=${random_seed}, workload_name_prefix=${workload_name_prefix}"

            # Run batsim in the background
            ${batsim} -m'graphene-1144.nancy.grid5000.fr' ${base_dir}/platforms/graphene.xml \
            "${base_dir}/workloads/${workload_name_prefix}seed${random_seed}_size${platform_size}.json" \
            -e "${workload_name_prefix}seed${random_seed}_size${platform_size}" \
            >batsim.stdout 2>batsim.stderr & batsim_pid=$!

            # Wait for socket creation
            while [[ -z $(grep '/tmp/bat_socket' /proc/net/unix) ]]
            do
                sleep 0.1
            done

            # Run scheduler
            if [ ${use_bataar} = true ]
            then
                ${sched} "${base_dir}/workloads/${workload_name_prefix}seed${random_seed}_size${platform_size}.json" \
                >sched.stdout 2>sched.stderr & sched_pid=$!
            else
                ${sched} -j "${base_dir}/workloads/${workload_name_prefix}seed${random_seed}_size${platform_size}.json" \
                -v conservative_bf \
                >sched.stdout 2>sched.stderr & sched_pid=$!
            fi

            # Sync
            wait ${batsim_pid}
            wait ${sched_pid}

            cd ${base_dir}
        done
    done
done

exit 0
