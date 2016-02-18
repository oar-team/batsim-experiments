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
        base_dir=$(pwd)
        mkdir -p "simulated_run/g5k_workload_msg_seed${random_seed}_size${platform_size}/output"
        cd "simulated_run/g5k_workload_msg_seed${random_seed}_size${platform_size}/output"

        echo "Running experiment random_seed=${random_seed}, platform_size=${platform_size}"

        # Run batsim in the background
        ${batsim} -m'graphene-1144.nancy.grid5000.fr' ${base_dir}/platforms/graphene.xml \
        "${base_dir}/workloads/g5k_workload_msg_seed${random_seed}_size${platform_size}.json" \
        -e "g5k_workload_msg_seed${random_seed}_size${platform_size}" \
        >batsim.stdout 2>batsim.stderr & batsim_pid=$!

        # Wait few seconds then run bataar
        sleep 2
        ${bataar} "${base_dir}/workloads/g5k_workload_msg_seed${random_seed}_size${platform_size}.json" \
        >bataar.stdout 2>bataar.stderr & bataar_pid=$!

        # Sync
        wait ${batsim_pid}
        wait ${bataar_pid}

        cd ${base_dir}
    done
done

exit 0
