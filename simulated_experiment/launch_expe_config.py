#!/usr/bin/python3

import argparse
import json
import os
import subprocess
import shutil
import time
from collections import OrderedDict

script_oar_gantt_to_csv = '../result_analysis/oar_result_to_batsim_csv.py'
script_r_compare_oar_batsim_jobs = '../result_analysis/compare_outputs.R'
script_r_analyse_schedule_jobs = '../result_analysis/analyse_schedule_jobs.R'
script_r_do_metrics_graphs_aggregated = '../result_analysis/do_metrics_graphs_aggregated.R'
script_draw_gantts = 'evalys'

def create_dir_if_not_exists(directory):
    if not os.path.exists(directory):
        os.makedirs(directory)

def remove_file_if_exists(filename):
    if os.path.exists(filename):
        os.remove(filename)

def remove_dir_if_exists(directory):
    if os.path.exists(directory):
        shutil.rmtree(directory)

def run_subprocess_do_not_wait(command, working_directory, stdout_file, stderr_file):
    return subprocess.Popen(command,
                            cwd = working_directory,
                            stdout = stdout_file,
                            stderr = stderr_file)

def wait_for_termination(process, timeout = None):
    (stdout, stderr) = process.communicate(timeout = timeout)

def run_write_output(command, working_directory, stdout_filename, stderr_filename, timeout = 2*60):
    stdout_file = open(stdout_filename, 'w+')
    stderr_file = open(stderr_filename, 'w+')
    try:
        process = run_subprocess_do_not_wait(command, working_directory, stdout_file, stderr_file)
        wait_for_termination(process, timeout)
    except subprocess.TimeoutExpired:
        print('Command {} reached timeout!'.format(command))
    except FileNotFoundError as e:
        (errno, strerror) = e.args
        print('Command {} could not be executed: {}'.format(command, strerror))

    stdout_file.close()
    stderr_file.close()

    return process.returncode == 0

def run_string_write_output(command_str, working_directory, stdout_filename, stderr_filename, timeout = 2*60):
    command = command_str.split(' ')
    return run_write_output(command, working_directory, stdout_filename, stderr_filename, timeout)

def socket_in_use(sock):
    return sock in open('/proc/net/unix').read()

def wait_for_batsim_to_open_connection(sock='/tmp/bat_socket', timeout=60, seconds_to_sleep=0.1):
    while timeout > 0 and not socket_in_use(sock):
        time.sleep(seconds_to_sleep)
    return timeout > 0

def execute_in_simulo(experiment,
                      experiment_name,
                      base_directory,
                      experiment_base_directory,
                      default_socket_creation_timeout = None,
                      default_timeout = None,
                      default_socket = '/tmp/bat_socket'):
    simulated_workload = str(experiment['simulated_workload'])
    simulated_platform = str(experiment['simulated_platform'])

    batsim_command_str = str(experiment['batsim_command'])
    sched_command_str = str(experiment['sched_command'])

    timeout = default_timeout
    if 'timeout' in experiment:
        timeout = float(experiment['timeout'])

    socket_creation_timeout = default_socket_creation_timeout
    if 'socket_creation_timeout' in experiment:
        socket_creation_timeout = float(experiment['socket_creation_timeout'])

    socket = default_socket
    if 'socket' in experiment:
        socket = str(experiment['socket'])

    # Let's check the commands
    if ('-e' in batsim_command_str) or ('--export' in batsim_command_str):
        return (False, 'batsim command line must NOT contain an export option')

    # Let's replace some strings in the commands!
    platform_full_name = '{base_dir}/{platform}'.format(
                            base_dir = base_directory,
                            platform = simulated_platform)
    workload_full_name = '{base_dir}/{workload}'.format(
                            base_dir = base_directory,
                            workload = simulated_workload)

    batsim_command_str = batsim_command_str.replace('PLATFORM', platform_full_name)
    batsim_command_str = batsim_command_str.replace('WORKLOAD', workload_full_name)

    sched_command_str = sched_command_str.replace('PLATFORM', platform_full_name)
    sched_command_str = sched_command_str.replace('WORKLOAD', workload_full_name)

    # Let's add the batsim export prefix
    batsim_command_str += ' --export batsim_{}_out'.format(experiment_name)

    # Let's create the real commands
    batsim_command = batsim_command_str.split(' ')
    sched_command = sched_command_str.split(' ')

    # Directory handling
    remove_dir_if_exists(experiment_name)
    create_dir_if_not_exists(experiment_name)

    # Let's run the experiment
    batsim_stdout_file = open('{exp_dir}/{exp_name}/batsim_{exp_name}.stdout'.format(
                            exp_dir = experiment_base_directory,
                            exp_name = experiment_name), 'w')
    batsim_stderr_file = open('{exp_dir}/{exp_name}/batsim_{exp_name}.stderr'.format(
                            exp_dir = experiment_base_directory,
                            exp_name = experiment_name), 'w')
    sched_stdout_file = open('{exp_dir}/{exp_name}/sched_{exp_name}.stdout'.format(
                            exp_dir = experiment_base_directory,
                            exp_name = experiment_name), 'w')
    sched_stderr_file = open('{exp_dir}/{exp_name}/sched_{exp_name}.stderr'.format(
                            exp_dir = experiment_base_directory,
                            exp_name = experiment_name), 'w')
    commands_file = open('{exp_dir}/{exp_name}/in_simulo_commands_{exp_name}.log'.format(
                        exp_dir = experiment_base_directory,
                        exp_name = experiment_name), 'w')
    commands_file.write('batsim : [{}]\n\n'.format(', '.join(batsim_command)))
    commands_file.write('batsim_str : {}\n\n'.format(' '.join(batsim_command)))
    commands_file.write('sched : [{}]\n\n'.format(', '.join(sched_command)))
    commands_file.write('sched_str : {}\n\n'.format(' '.join(sched_command)))
    commands_file.close()

    success = False
    reason = ''
    remove_file_if_exists(socket)
    try:
        batsim_launched = True
        batsim_process = run_subprocess_do_not_wait(command = batsim_command,
                                                    working_directory = '{exp_dir}/{exp_name}'.format(
                                                        exp_dir = experiment_base_directory,
                                                        exp_name = experiment_name),
                                                    stdout_file = batsim_stdout_file,
                                                    stderr_file = batsim_stderr_file)
    except FileNotFoundError as e:
        (errno, strerror) = e.args
        reason = 'cannot launch batsim. ' + strerror
        batsim_launched = False

    if batsim_launched:
        if wait_for_batsim_to_open_connection(timeout = socket_creation_timeout):
            sched_launched = True
            try:
                sched_process = run_subprocess_do_not_wait(command = sched_command,
                                                           working_directory = '{exp_dir}/{exp_name}'.format(
                                                            exp_dir = experiment_base_directory,
                                                            exp_name = experiment_name),
                                                           stdout_file = sched_stdout_file,
                                                           stderr_file = sched_stderr_file)
            except FileNotFoundError as e:
                (errno, strerror) = e.args
                reason = 'cannot launch scheduler. ' + strerror
                sched_launched = False
            if sched_launched:
                try:
                    wait_for_termination(sched_process, timeout = timeout)
                    wait_for_termination(batsim_process, timeout = timeout)

                    # Let's check return values
                    if (sched_process.returncode != 0) or (batsim_process.returncode != 0):
                        reason = 'bad returncode (batsim={}, sched={})'.format(batsim_process.returncode,
                                                                               sched_process.returncode)
                    else:
                        success = True
                except subprocess.TimeoutExpired:
                    reason = 'execution timeout reached :('
                sched_process.kill()
        else:
            reason ='cannot reach batsim socket creation :('
        batsim_process.kill()

    batsim_stdout_file.close()
    batsim_stderr_file.close()
    sched_stdout_file.close()
    sched_stderr_file.close()

    return (success, reason)

def compare_to_oar(experiment,
                   experiment_name,
                   base_directory,
                   experiment_base_directory,
                   default_simulation_model):
    # Let's check that all needed parameters are in the experiment

    if not 'oar_instances' in experiment:
        reason = "Invalid experiment {}: no 'oar_instances' field set whereas this experiment should be compared to an OAR output".format(experiment_name)
        return (False, reason)

    for oar_instance_name in experiment['oar_instances']:
        oar_instance = experiment['oar_instances'][oar_instance_name]

        oar_output_directory = ''
        oar_job_id_mapping = ''
        oar_gantt_json_filename = ''
        oar_gantt_json_details_filename = ''
        graph_dir = 'graphs'

        if 'oar_output_directory' in oar_instance:
            oar_output_directory = str(oar_instance['oar_output_directory'])
        if 'oar_job_id_mapping' in oar_instance:
            oar_job_id_mapping = str(oar_instance['oar_job_id_mapping'])
        if 'oar_gantt_json_filename' in oar_instance:
            oar_gantt_json_filename = str(oar_instance['oar_gantt_json_filename'])
        if 'oar_gantt_json_details_filename' in oar_instance:
            oar_gantt_json_details_filename = str(oar_instance['oar_gantt_json_details_filename'])

        all_fields_set = bool(oar_output_directory) and bool(oar_job_id_mapping) and bool(oar_gantt_json_filename) and bool(oar_gantt_json_details_filename)

        if not all_fields_set:
            reason = "Invalid experiment {}: oar_instance {} does not have required fields for a compare_to_oar experiment, which are 'oar_output_directory', 'oar_job_id_mapping', 'oar_gantt_json_filename' and 'oar_gantt_json_details_filename'".format(experiment_name, oar_instance_name)
            return (False, reason)

        create_dir_if_not_exists('{exp_dir}/{exp_name}/oar_{oar_instance_name}'.format(
            exp_dir = experiment_base_directory,
            exp_name = experiment_name,
            oar_instance_name = oar_instance_name))

        # Let's create a CSV for the real OAR gantt
        build_csv_command = 'python3 {base_dir}/{script} -r -z -m {base_dir}/{oar_dir}/{mapping} {base_dir}/{oar_dir}/{gantt} {exp_dir}/{exp_name}/oar_{oar_instance_name}/oar_{exp_name}_{oar_instance_name}_out_jobs.csv'.format(
            base_dir = base_directory,
            script = script_oar_gantt_to_csv,
            oar_dir = oar_output_directory,
            mapping = oar_job_id_mapping,
            gantt = oar_gantt_json_filename,
            exp_dir = experiment_base_directory,
            exp_name = experiment_name,
            oar_instance_name = oar_instance_name)
        if not run_string_write_output(command_str = build_csv_command,
                                       working_directory = '{exp_dir}/{exp_name}/oar_{oar_instance_name}'.format(
                                            exp_dir = experiment_base_directory,
                                            exp_name = experiment_name,
                                            oar_instance_name = oar_instance_name),
                                       stdout_filename = '{exp_dir}/{exp_name}/oar_{oar_instance_name}/oar_{exp_name}_gantt_to_csv.stdout'.format(
                                            exp_dir = experiment_base_directory,
                                            exp_name = experiment_name,
                                            oar_instance_name = oar_instance_name),
                                       stderr_filename = '{exp_dir}/{exp_name}/oar_{oar_instance_name}/oar_{exp_name}_gantt_to_csv.stderr'.format(
                                            exp_dir = experiment_base_directory,
                                            exp_name = experiment_name,
                                            oar_instance_name = oar_instance_name)):
            reason ='cannot build the jobs CSV from the OAR gantt'
            return (False, reason)

        # Let's create the graph output directory
        create_dir_if_not_exists('{exp_dir}/{exp_name}/oar_{oar_instance_name}/{graph_dir}'.format(
                                    exp_dir = experiment_base_directory,
                                    exp_name = experiment_name,
                                    oar_instance_name = oar_instance_name,
                                    graph_dir = graph_dir))

        # Let's run the R script to compare Batsim's and OAR's jobs CSVs
        compare_csv_command = 'Rscript --vanilla {base_dir}/{script} {batsim_jobs_csv} {oar_jobs_csv} {graph_dir}'.format(
            base_dir = base_directory,
            script = script_r_compare_oar_batsim_jobs,
            batsim_jobs_csv = '{exp_dir}/{exp_name}/batsim_{exp_name}_out_jobs.csv'.format(
                exp_dir = experiment_base_directory,
                exp_name = experiment_name),
            oar_jobs_csv = '{exp_dir}/{exp_name}/oar_{oar_instance_name}/oar_{exp_name}_{oar_instance_name}_out_jobs.csv'.format(
                exp_dir = experiment_base_directory,
                exp_name = experiment_name,
                oar_instance_name = oar_instance_name),
            graph_dir = '{exp_dir}/{exp_name}/oar_{oar_instance_name}/{graph_dir}'.format(
                exp_dir = experiment_base_directory,
                exp_name = experiment_name,
                graph_dir = graph_dir,
                oar_instance_name = oar_instance_name))
        if not run_string_write_output(command_str = compare_csv_command,
                                       working_directory = '{exp_dir}/{exp_name}/oar_{oar_instance_name}'.format(
                                            exp_dir = experiment_base_directory,
                                            exp_name = experiment_name,
                                            oar_instance_name = oar_instance_name),
                                       stdout_filename = '{exp_dir}/{exp_name}/oar_{oar_instance_name}/compare_batsim_oar_csv_{exp_name}.stdout'.format(
                                            exp_dir = experiment_base_directory,
                                            exp_name = experiment_name,
                                            oar_instance_name = oar_instance_name),
                                       stderr_filename = '{exp_dir}/{exp_name}/oar_{oar_instance_name}/compare_batsim_oar_csv_{exp_name}.stderr'.format(
                                            exp_dir = experiment_base_directory,
                                            exp_name = experiment_name,
                                            oar_instance_name = oar_instance_name)):
            reason = "cannot compute graphs comparing Batsim's and OAR's jobs CSVs"
            return (False, reason)

        # Let's draw the Gantt charts of the schedules
        draw_gantt_charts_command = '{script} -o {exp_dir}/{exp_name}/oar_{oar_instance_name}/gantts_{exp_name}.pdf -s {exp_dir}/{exp_name}/batsim_{exp_name}_out_jobs.csv {exp_dir}/{exp_name}/oar_{oar_instance_name}/oar_{exp_name}_{oar_instance_name}_out_jobs.csv'.format(
            script = script_draw_gantts,
            exp_dir = experiment_base_directory,
            exp_name = experiment_name,
            oar_instance_name = oar_instance_name)
        run_string_write_output(command_str = draw_gantt_charts_command,
                                working_directory = '{exp_dir}/{exp_name}/oar_{oar_instance_name}'.format(
                                    exp_dir = experiment_base_directory,
                                    exp_name = experiment_name,
                                    oar_instance_name = oar_instance_name),
                                stdout_filename = '{exp_dir}/{exp_name}/oar_{oar_instance_name}/draw_gantts_{exp_name}.stdout'.format(
                                    exp_dir = experiment_base_directory,
                                    exp_name = experiment_name,
                                    oar_instance_name = oar_instance_name),
                                stderr_filename = '{exp_dir}/{exp_name}/oar_{oar_instance_name}/draw_gantts_{exp_name}.stderr'.format(
                                    exp_dir = experiment_base_directory,
                                    exp_name = experiment_name,
                                    oar_instance_name = oar_instance_name))

    return (True, '')


def aggregate_results(experiments,
                      successful_experiment_names,
                      bounded_slowdown_min_runtime,
                      aggregated_directory,
                      base_directory,
                      experiment_base_directory,
                      default_simulation_model):
    schedule_metrics_filename = 'schedule_metrics.csv'
    print('Aggregating results...')
    print('bounded_slowdown_min_runtime = ', bounded_slowdown_min_runtime)
    # Let's compute some metrics on each schedule thanks to a R script
    print('Computing scheduling metrics on each successful experiment')
    for experiment_name in successful_experiment_names:
        experiment = experiments[experiment_name]
        simulation_model = default_simulation_model
        if 'simulation_model' in experiment:
            simulation_model = str(experiment['simulation_model'])
        # Rscript --vanilla analyse_schedule_jobs.R JOBS OUTPUT_METRICS_FILE WORKLOAD_NAME WORKLOAD_TYPE BOUNDED_STRETCH_MIN_RUNTIME
        compute_metrics_command = 'Rscript --vanilla {base_dir}/{script} {exp_dir}/{exp_name}/batsim_{exp_name}_out_jobs.csv {exp_dir}/{exp_name}/{exp_name}_{workload_type}_{schedule_metrics_filename} {exp_name} {workload_type} {bounded_slowdown_min_runtime}'.format(
            base_dir = base_directory,
            script = script_r_analyse_schedule_jobs,
            exp_dir = experiment_base_directory,
            exp_name = experiment_name,
            workload_type = simulation_model,
            bounded_slowdown_min_runtime = bounded_slowdown_min_runtime,
            schedule_metrics_filename = schedule_metrics_filename)
        run_string_write_output(command_str = compute_metrics_command,
                                working_directory = '{exp_dir}/{exp_name}'.format(exp_dir=experiment_base_directory, exp_name=experiment_name),
                                stdout_filename = '{exp_dir}/{exp_name}/compute_metrics_{exp_name}_{workload_type}.stdout'.format(
                                    exp_dir = experiment_base_directory,
                                    exp_name = experiment_name,
                                    workload_type = simulation_model),
                                stderr_filename = '{exp_dir}/{exp_name}/compute_metrics_{exp_name}_{workload_type}.stderr'.format(
                                    exp_dir = experiment_base_directory,
                                    exp_name = experiment_name,
                                    workload_type = simulation_model))



        if ('compare_to_oar' in experiment) and (bool(experiment['compare_to_oar'])):
            for oar_instance_name in experiment['oar_instances']:
                compute_metrics_command = 'Rscript --vanilla {base_dir}/{script} {exp_dir}/{exp_name}/oar_{oar_instance_name}/oar_{exp_name}_{oar_instance_name}_out_jobs.csv {exp_dir}/{exp_name}/oar_{oar_instance_name}/{exp_name}_{workload_type}_{schedule_metrics_filename} {exp_name} {workload_type} {bounded_slowdown_min_runtime}'.format(
                    base_dir = base_directory,
                    script = script_r_analyse_schedule_jobs,
                    exp_dir = experiment_base_directory,
                    exp_name = experiment_name,
                    oar_instance_name = oar_instance_name,
                    workload_type = 'real',
                    bounded_slowdown_min_runtime = bounded_slowdown_min_runtime,
                    schedule_metrics_filename = schedule_metrics_filename)
                run_string_write_output(command_str = compute_metrics_command,
                                        working_directory = '{exp_dir}/{exp_name}/oar_{oar_instance_name}'.format(
                                            exp_dir = experiment_base_directory,
                                            exp_name = experiment_name,
                                            oar_instance_name = oar_instance_name),
                                        stdout_filename = '{exp_dir}/{exp_name}/oar_{oar_instance_name}/compute_metrics_{exp_name}_{workload_type}.stdout'.format(
                                            exp_dir = experiment_base_directory,
                                            exp_name = experiment_name,
                                            workload_type = 'real',
                                            oar_instance_name = oar_instance_name),
                                        stderr_filename = '{exp_dir}/{exp_name}/oar_{oar_instance_name}/compute_metrics_{exp_name}_{workload_type}.stderr'.format(
                                            exp_dir = experiment_base_directory,
                                            exp_name = experiment_name,
                                            workload_type = 'real',
                                            oar_instance_name = oar_instance_name))


    # Merging metrics in the same file
    print('Merging metrics in the same file...')
    create_dir_if_not_exists('{exp_dir}/{agg_dir}'.format(
                                exp_dir = experiment_base_directory,
                                agg_dir = aggregated_directory))

    with open('{exp_dir}/{agg_dir}/{schedule_metrics_filename}'.format(
                exp_dir = experiment_base_directory,
                agg_dir = aggregated_directory,
                schedule_metrics_filename = schedule_metrics_filename), 'w+') as output_file:
        # Let's copy the first line of one metrics result to retrieve the CSV header
        with open('{exp_dir}/{exp_name}/{exp_name}_{workload_type}_{schedule_metrics_filename}'.format(
                    exp_dir = experiment_base_directory,
                    exp_name = successful_experiment_names[0],
                    workload_type = simulation_model,
                    schedule_metrics_filename = schedule_metrics_filename), 'r') as input_file:
            content = input_file.readlines()
            line = content[0]
            output_file.write(line)
            input_file.close()

        # Let's add the second lines of all metrics result files and append them in our aggregated output file
        for experiment_name in successful_experiment_names:
            with open('{exp_dir}/{exp_name}/{exp_name}_{workload_type}_{schedule_metrics_filename}'.format(
                    exp_dir = experiment_base_directory,
                    exp_name = experiment_name,
                    workload_type = simulation_model,
                    schedule_metrics_filename = schedule_metrics_filename), 'r') as input_file:
                content = input_file.readlines()
                line = content[1]
                output_file.write(line)
                input_file.close()
            experiment = experiments[experiment_name]
            if ('compare_to_oar' in experiment) and (bool(experiment['compare_to_oar'])):
                for oar_instance_name in experiment['oar_instances']:
                    with open('{exp_dir}/{exp_name}/oar_{oar_instance_name}/{exp_name}_{workload_type}_{schedule_metrics_filename}'.format(
                                exp_dir = experiment_base_directory,
                                exp_name = experiment_name,
                                oar_instance_name = oar_instance_name,
                                workload_type = 'real',
                                schedule_metrics_filename = schedule_metrics_filename), 'r') as input_file:
                        content = input_file.readlines()
                        line = content[1]
                        output_file.write(line)
                        input_file.close()

        output_file.close()

    print('Generating graphs...')
    graph_dir = 'graphs'
    create_dir_if_not_exists('{exp_dir}/{agg_dir}/{graph_dir}'.format(
                                exp_dir = experiment_base_directory,
                                agg_dir = aggregated_directory,
                                graph_dir = graph_dir))
    aggregated_graphs_command = 'Rscript --vanilla {base_dir}/{script} {exp_dir}/{agg_dir}/{schedule_metrics_filename} {exp_dir}/{agg_dir}/{graph_dir}'.format(
        base_dir = base_directory,
        script = script_r_do_metrics_graphs_aggregated,
        exp_dir = experiment_base_directory,
        agg_dir = aggregated_directory,
        schedule_metrics_filename = schedule_metrics_filename,
        graph_dir = graph_dir)
    run_string_write_output(command_str = aggregated_graphs_command,
                            working_directory = '{exp_dir}/{agg_dir}'.format(
                                exp_dir = experiment_base_directory,
                                agg_dir = aggregated_directory),
                            stdout_filename = '{exp_dir}/{agg_dir}/do_graphs.stdout'.format(
                                exp_dir = experiment_base_directory,
                                agg_dir = aggregated_directory),
                            stderr_filename = '{exp_dir}/{agg_dir}/do_graphs.stderr'.format(
                                exp_dir = experiment_base_directory,
                                agg_dir = aggregated_directory))

    # Generating the aggregated gantt chart
    print('Generating the aggregated gantt charts')
    aggregated_draw_gantt_charts_command = '{script} -o {exp_dir}/{agg_dir}/gantts.pdf {out_job_filenames}'.format(
        script = script_draw_gantts,
        exp_dir = experiment_base_directory,
        agg_dir = aggregated_directory,
        out_job_filenames = ' '.join(['{exp_dir}/{exp_name}/batsim_{exp_name}_out_jobs.csv'.format(
            exp_dir = experiment_base_directory,
            exp_name = experiment_name) for experiment_name in successful_experiment_names]))
    print(aggregated_draw_gantt_charts_command)
    run_string_write_output(command_str = aggregated_draw_gantt_charts_command,
                            working_directory = '{exp_dir}/{agg_dir}'.format(
                                exp_dir = experiment_base_directory,
                                agg_dir = aggregated_directory),
                            stdout_filename = '{exp_dir}/{agg_dir}/draw_gantts.stdout'.format(
                                exp_dir = experiment_base_directory,
                                agg_dir = aggregated_directory),
                            stderr_filename = '{exp_dir}/{agg_dir}/draw_gantts.stderr'.format(
                                exp_dir = experiment_base_directory,
                                agg_dir = aggregated_directory))


def launch_experiment(config_json_filename):
    json_file = open(config_json_filename, 'r')
    json_data = json.load(json_file, object_pairs_hook=OrderedDict)

    output_directory = str(json_data['output_directory'])
    create_dir_if_not_exists(output_directory)

    default_timeout = None
    if 'default_timeout' in json_data:
        default_timeout = float(json_data['default_timeout'])

    default_socket_creation_timeout = 60
    if 'default_socket_creation_timeout' in json_data:
        default_socket_creation_timeout = float(json_data['default_socket_creation_timeout'])

    default_socket = '/tmp/bat_socket'
    if 'default_socket' in json_data:
        default_socket = str(json_data['default_socket'])

    default_simulation_model = "unset",
    if 'default_simulation_model' in json_data:
        default_simulation_model = str(json_data['default_simulation_model'])

    default_generate_gantt_evalys = False
    if 'default_generate_gantt_evalys' in json_data:
        default_generate_gantt_evalys = bool(json_data['default_generate_gantt_evalys'])

    base_directory = os.getcwd()
    os.chdir(os.getcwd() + '/' + output_directory)
    experiment_base_directory = os.getcwd()

    must_aggregate_results = False
    if 'aggregate_results' in json_data:
        must_aggregate_results = bool(json_data['aggregate_results'])

    aggregated_directory = 'aggregated'
    if 'aggregated_directory' in json_data:
        aggregated_directory = str(json_data['aggregated_directory'])

    bounded_slowdown_min_runtime = 60
    if 'bounded_slowdown_min_runtime' in json_data:
        bounded_slowdown_min_runtime = float(json_data['bounded_slowdown_min_runtime'])

    nb_experiments = len(json_data['experiments'])
    curr_experiment_number = 1
    successful_experiments = []
    failed_experiments = []

    for experiment_name in json_data['experiments']:
        print('Starting experiment {curr_exp_nb}/{nb_exp} ({percentage} %): {exp_name}'.format(
                curr_exp_nb = curr_experiment_number,
                nb_exp = nb_experiments,
                percentage = (curr_experiment_number * 100) / nb_experiments,
                exp_name = experiment_name))

        experiment = json_data['experiments'][experiment_name]
        (success, reason) = execute_in_simulo(experiment = experiment,
                                              experiment_name = experiment_name,
                                              base_directory = base_directory,
                                              experiment_base_directory = experiment_base_directory,
                                              default_socket_creation_timeout = default_socket_creation_timeout,
                                              default_timeout = default_timeout,
                                              default_socket = default_socket)

        if success:
            generate_gantt_chart_evalys = default_generate_gantt_evalys
            if 'generate_gantt_chart_evalys' in experiment:
                generate_gantt_chart_evalys = bool(experiment['generate_gantt_chart_evalys'])

            if generate_gantt_chart_evalys:
                draw_gantt_charts_command = '{script} -o {exp_dir}/{exp_name}/gantt.pdf {exp_dir}/{exp_name}/batsim_{exp_name}_out_jobs.csv'.format(
                    script = script_draw_gantts,
                    exp_dir = experiment_base_directory,
                    exp_name = experiment_name)
                run_string_write_output(command_str = draw_gantt_charts_command,
                                        working_directory = '{exp_dir}/{exp_name}'.format(
                                            exp_dir = experiment_base_directory,
                                            exp_name = experiment_name),
                                        stdout_filename = '{exp_dir}/{exp_name}/draw_gantts_{exp_name}.stdout'.format(
                                            exp_dir = experiment_base_directory,
                                            exp_name = experiment_name),
                                        stderr_filename = '{exp_dir}/{exp_name}/draw_gantts_{exp_name}.stderr'.format(
                                            exp_dir = experiment_base_directory,
                                            exp_name = experiment_name))

            if ('compare_to_oar' in experiment) and (bool(experiment['compare_to_oar'])):
                (success, reason) = compare_to_oar(experiment = experiment,
                                                   experiment_name = experiment_name,
                                                   base_directory = base_directory,
                                                   experiment_base_directory = experiment_base_directory,
                                                   default_simulation_model = default_simulation_model)
                if not success:
                    failed_experiments.append(experiment_name)
                    print('FAILED: ' + reason)
                else:
                    if ('test_noise_impact' in experiment) and (bool(experiment['test_noise_impact'])):
                        (success, reason) = test_noise_impact(experiment = experiment,
                                                              experiment_name = experiment_name,
                                                              base_directory = base_directory,
                                                              experiment_base_directory = experiment_base_directory)
                        if success:
                            successful_experiments.append(experiment_name)
                        else:
                            failed_experiments.append(experiment_name)
                            print('FAILED: ' + reason)
                    else:
                        successful_experiments.append(experiment_name)
            else:
                successful_experiments.append(experiment_name)
        else:
            failed_experiments.append(experiment_name)
            print('FAILED: ' + reason)

        curr_experiment_number += 1

    print('All experiments have been executed')
    if len(failed_experiments) == 0:
        print('Everything seemed to be executed correctly')
    else:
        print('{} experiments failed : [{}]'.format(len(failed_experiments), ', '.join(failed_experiments)))

    if must_aggregate_results and len(successful_experiments) > 0:
        aggregate_results(experiments = json_data['experiments'],
                          successful_experiment_names = successful_experiments,
                          bounded_slowdown_min_runtime = bounded_slowdown_min_runtime,
                          aggregated_directory = aggregated_directory,
                          base_directory = base_directory,
                          experiment_base_directory = experiment_base_directory,
                          default_simulation_model = default_simulation_model)

def main():
    # Program parameters parsing
    parser = argparse.ArgumentParser(description='Launches an experiment according to a configuration file')
    parser.add_argument('experiment_config_json', type=str,
                        help='The input configuration JSON file which describes the experiment to run')

    args = parser.parse_args()
    launch_experiment(args.experiment_config_json)

if __name__ == '__main__':
    main()
