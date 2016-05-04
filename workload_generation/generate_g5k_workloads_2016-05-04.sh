#!/usr/bin/bash

translate_script='translate_submission_times.py'

output_dir='generated_workloads/2016-05-04'

mkdir -p ${output_dir}

for platform_size in 32
do
    for random_seed in {0..9}
    do
        output_filename="g5k_workload_delay_seed${random_seed}_size${platform_size}.json"
        job_number=800
        interarrival_times_weibull_shape=2
        interarrival_times_weibull_scale=15
        job_sizes_lognormal_mean=0.25
        job_sizes_lognormal_standard_deviation=0.5
        maximum_job_length=600

        python3 json_workload_generator.py -i 4 profiles/delay_profiles_mpi_commands.json \
            "${output_dir}/${output_filename}" "${platform_size}" -jn "${job_number}" \
            -lambda "${interarrival_times_weibull_scale}" -k "${interarrival_times_weibull_shape}" \
            -mu "${job_sizes_lognormal_mean}" -sigma "${job_sizes_lognormal_standard_deviation}" \
            -rs "${random_seed}" --maximum_job_length "${maximum_job_length}"

        python3 "${translate_script}" -i 4 -w "${output_dir}/${output_filename}"
    done
done
