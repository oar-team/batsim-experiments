#!/usr/bin/python3

import argparse
import json
import os
import subprocess
import shutil
import time

script_oar_gantt_to_csv = '../result_analysis/oar_result_to_batsim_csv.py'
script_r_compare_oar_batsim_jobs = '../result_analysis/compare_outputs.R'
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
                            stdout=stdout_file,
                            stderr=stderr_file)

def wait_for_termination(process, timeout=None):
    (stdout, stderr) = process.communicate(timeout=timeout)

def run_write_output(command, working_directory, stdout_filename, stderr_filename, timeout=2*60):
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

def run_string_write_output(command_str, working_directory, stdout_filename, stderr_filename, timeout=2*60):
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
                      default_socket_creation_timeout=None,
                      default_timeout=None,
                      default_socket='/tmp/bat_socket'):
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
    batsim_command_str = batsim_command_str.replace('PLATFORM', base_directory + '/' + simulated_platform)
    batsim_command_str = batsim_command_str.replace('WORKLOAD', base_directory + '/' + simulated_workload)

    sched_command_str = sched_command_str.replace('PLATFORM', base_directory + '/' + simulated_platform)
    sched_command_str = sched_command_str.replace('WORKLOAD', base_directory + '/' + simulated_workload)

    # Let's add the batsim export prefix
    batsim_command_str += ' --export batsim_out'

    # Let's create the real commands
    batsim_command = batsim_command_str.split(' ')
    sched_command = sched_command_str.split(' ')

    # Directory handling
    os.chdir(experiment_base_directory)
    remove_dir_if_exists(experiment_name)
    create_dir_if_not_exists(experiment_name)
    os.chdir(os.getcwd() + '/' + experiment_name)

    # Let's run the experiment
    batsim_stdout_file = open(os.getcwd() + '/batsim.stdout', 'w')
    batsim_stderr_file = open(os.getcwd() + '/batsim.stderr', 'w')
    sched_stdout_file = open(os.getcwd() + '/sched.stdout', 'w')
    sched_stderr_file = open(os.getcwd() + '/sched.stderr', 'w')
    commands_file = open(os.getcwd() + '/in_simulo_commands.log', 'w')
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
                                                    working_directory = os.getcwd(),
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
                                                           working_directory = os.getcwd(),
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
                   experiment_base_directory):
    # Let's check that all needed parameters are in the experiment
    oar_output_directory = ''
    oar_job_id_mapping = ''
    oar_gantt_json_filename = ''
    oar_gantt_json_details_filename = ''

    if 'oar_output_directory' in experiment:
        oar_output_directory = str(experiment['oar_output_directory'])
    if 'oar_job_id_mapping' in experiment:
        oar_job_id_mapping = str(experiment['oar_job_id_mapping'])
    if 'oar_gantt_json_filename' in experiment:
        oar_gantt_json_filename = str(experiment['oar_gantt_json_filename'])
    if 'oar_gantt_json_details_filename' in experiment:
        oar_gantt_json_details_filename = str(experiment['oar_gantt_json_details_filename'])

    all_fields_set = bool(oar_output_directory) and bool(oar_job_id_mapping) and bool(oar_gantt_json_filename) and bool(oar_gantt_json_details_filename)

    if not all_fields_set:
        reason = "Invalid experiment {}: required fields for a compare_to_oar experiment are 'oar_output_directory', 'oar_job_id_mapping', 'oar_gantt_json_filename', 'oar_gantt_json_details_filename'".format(experiment_name)
        return (False, reason)

    os.chdir(experiment_base_directory)
    create_dir_if_not_exists(experiment_name)
    os.chdir(os.getcwd() + '/' + experiment_name)

    # Let's create a CSV for the real OAR gantt
    build_csv_command = 'python3 {base_dir}/{script} -r -z -m {base_dir}/{oar_dir}/{mapping} {base_dir}/{oar_dir}/{gantt} {cwd}/oar_out_jobs.csv'.format(
        base_dir = base_directory,
        script = script_oar_gantt_to_csv,
        oar_dir = oar_output_directory,
        mapping = oar_job_id_mapping,
        gantt = oar_gantt_json_filename,
        cwd = os.getcwd())
    if not run_string_write_output(command_str = build_csv_command, working_directory = os.getcwd(),
                                   stdout_filename = os.getcwd() + "/oar_gantt_to_csv.stdout",
                                   stderr_filename = os.getcwd() + "/oar_gantt_to_csv.stderr"):
        reason ='cannot build the jobs CSV from the OAR gantt'
        return (False, reason)

    # Let's create the graph output directory
    create_dir_if_not_exists(os.getcwd() + '/graphs')

    # Let's run the R script to compare Batsim's and OAR's jobs CSVs
    compare_csv_command = 'Rscript --vanilla {base_dir}/{script} {batsim_jobs_csv} {real_oar_jobs_csv} {graph_dir}'.format(
        base_dir = base_directory,
        script = script_r_compare_oar_batsim_jobs,
        batsim_jobs_csv = os.getcwd() + '/batsim_out_jobs.csv',
        real_oar_jobs_csv = os.getcwd() + '/oar_out_jobs.csv',
        graph_dir = os.getcwd() + '/graphs')
    if not run_string_write_output(command_str = compare_csv_command,
                                   working_directory = os.getcwd(),
                                   stdout_filename = os.getcwd() + '/compare_batsim_oar_csv.stdout',
                                   stderr_filename = os.getcwd() + '/compare_batsim_oar_csv.stderr'):
        reason = "cannot compute graphs comparing Batsim's and OAR's jobs CSVs"
        return (False, reason)

    # Let's draw the Gantt charts of the schedules
    draw_gantt_charts_command = '{script} -o {cwd}/gantts.svg {cwd}/batsim_out_jobs.csv {cwd}/oar_out_jobs.csv'.format(
        script = script_draw_gantts,
        cwd = os.getcwd())
    run_string_write_output(command_str = draw_gantt_charts_command,
                            working_directory = os.getcwd(),
                            stdout_filename = os.getcwd() + '/draw_gantt_charts_svg.stdout',
                            stderr_filename = os.getcwd() + '/draw_gantt_charts_svg.stderr')

    draw_gantt_charts_command = '{script} -o {cwd}/gantts.png {cwd}/batsim_out_jobs.csv {cwd}/oar_out_jobs.csv'.format(
        script = script_draw_gantts,
        cwd = os.getcwd())
    run_string_write_output(command_str = draw_gantt_charts_command,
                            working_directory = os.getcwd(),
                            stdout_filename = os.getcwd() + '/draw_gantt_charts_png.stdout',
                            stderr_filename = os.getcwd() + '/draw_gantt_charts_png.stderr')

    return (True, '')

def launch_experiment(config_json_filename):
    json_file = open(config_json_filename, 'r')
    json_data = json.load(json_file)

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

    base_directory = os.getcwd()
    os.chdir(os.getcwd() + '/' + output_directory)
    experiment_base_directory = os.getcwd()

    aggregate_results = False
    if 'aggregate_results' in json_data:
        aggregate_results = bool(json_data['aggregate_results'])

    nb_experiments = len(json_data['experiments'])
    curr_experiment_number = 1
    failed_experiments = []

    for experiment_name in json_data['experiments']:
        print('Starting experiment {}/{} ({} %): {}'.format(curr_experiment_number,
                                                            nb_experiments,
                                                            (curr_experiment_number * 100) / nb_experiments,
                                                            experiment_name))

        experiment = json_data['experiments'][experiment_name]
        (success, reason) = execute_in_simulo(experiment = experiment,
                                              experiment_name = experiment_name,
                                              base_directory = base_directory,
                                              experiment_base_directory = experiment_base_directory,
                                              default_socket_creation_timeout = default_socket_creation_timeout,
                                              default_timeout = default_timeout,
                                              default_socket = default_socket)

        if success:
            if ('compare_to_oar' in experiment) and (bool(experiment['compare_to_oar'])):
                (success, reason) = compare_to_oar(experiment = experiment,
                                                   experiment_name = experiment_name,
                                                   base_directory = base_directory,
                                                   experiment_base_directory = experiment_base_directory)
                if not success:
                    failed_experiments.append(experiment_name)
                    print('FAILED: ' + reason)
                else:
                    if ('test_noise_impact' in experiment) and (bool(experiment['test_noise_impact'])):
                        (success, reason) = test_noise_impact(experiment = experiment,
                                                              experiment_name = experiment_name,
                                                              base_directory = base_directory,
                                                              experiment_base_directory = experiment_base_directory)
        else:
            failed_experiments.append(experiment_name)
            print('FAILED: ' + reason)

        curr_experiment_number += 1

    print('All experiments have been executed')
    if len(failed_experiments) == 0:
        print('Everything seemed to be executed correctly')
    else:
        print('{} experiments failed : [{}]'.format(len(failed_experiments), ', '.join(failed_experiments)))

def main():
    # Program parameters parsing
    parser = argparse.ArgumentParser(description='Launches an experiment according to a configuration file')
    parser.add_argument('experiment_config_json', type=str,
                        help='The input configuration JSON file which describes the experiment to run')

    args = parser.parse_args()
    launch_experiment(args.experiment_config_json)

if __name__ == '__main__':
    main()
