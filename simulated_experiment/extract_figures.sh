#!/usr/bin/bash -e

if [ $# -ne 1 ]
then
    echo "Usage: $0 OUTPUT_DIRECTORY"
    exit 1
fi

output_dir=$1
input_dir="simulated_run_2016-02-20_13_22"

good_wload_dir="g5k_workload_merged_msg_seed1_size37"
bad_wload_dir="g5k_workload_merged_msg_seed4_size37"

base_dir=$(pwd)

# Good workload
cd ${input_dir}/${good_wload_dir}/graphs
cp execution_times_scatterplot.pdf ${output_dir}/good_wload_seed1_size37_execution_times_scatterplot.pdf
cp turnaround_times_scatterplot.pdf ${output_dir}/good_wload_seed1_size37_turnaround_times_scatterplot.pdf
cp turnaround_times_distribution_density.pdf ${output_dir}/good_wload_seed1_size37_turnaround_times_distribution_density.pdf
cp submission_time_difference.pdf ${output_dir}/good_wload_seed1_size37_submission_time_difference.pdf
cp execution_time_difference_color.pdf ${output_dir}/good_wload_seed1_size37_execution_time_difference_color.pdf

# Bad workload
cd ${base_dir}
cd ${input_dir}/${bad_wload_dir}/graphs
cp execution_times_scatterplot.pdf ${output_dir}/bad_wload_seed4_size37_execution_times_scatterplot.pdf
cp turnaround_times_scatterplot.pdf ${output_dir}/bad_wload_seed4_size37_turnaround_times_scatterplot.pdf
cp turnaround_times_distribution_density.pdf ${output_dir}/bad_wload_seed4_size37_turnaround_times_distribution_density.pdf
cp submission_time_difference.pdf ${output_dir}/bad_wload_seed4_size37_submission_time_difference.pdf
cp execution_time_difference_color.pdf ${output_dir}/bad_wload_seed4_size37_execution_time_difference_color.pdf

exit 0
