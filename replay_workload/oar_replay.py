#!/usr/bin/env python3
'''
This script is taking a Batsim profile as input and replay the profile
using the provided commands.
'''
import argparse
import json
import sched
import time
from subprocess import call, Popen, PIPE
from datetime import datetime, timedelta

command_path = "/home/mmercier/expe-batsim/workload_generation/NPB_bin/"


def do_oar_submission(command, walltime, resources, hostfile_dir):
    hms_time = timedelta(seconds=walltime)
    oar_time = str(hms_time).split('.')[0]
    exports = 'export PATH=$PATH:{}; export HOSTDIR={};'.format(command_path, hostfile_dir)
    oar_options = '--stdout={result_dir}/OAR%jobid%.stdout --stderr={result_dir}/OAR%jobid%.stderr '.format(result_dir=hostfile_dir)
    oar_cmd = (exports + 'oarsub ' + oar_options + ' -l \\nodes=' + str(resources) + ',walltime=' +
               oar_time + ' "' + command + '"')
    print(oar_cmd)
    call(oar_cmd, shell=True)


def get_scheduling_results(results_file):
    fmt = '%Y-%m-%d %X'
    oar_gantt_cmd = ('oarstat -J --gantt "' + begin.strftime(fmt) + ',' +
                     end.strftime(fmt) + '" > ' + str(results_file))
    print(oar_gantt_cmd)
    call(oar_gantt_cmd,
         shell=True)

parser = argparse.ArgumentParser(description='Replay Batsim profile using'
                                             'OAR submitions')
parser.add_argument('inputJSON',
                    type=argparse.FileType('r'),
                    help='The input JSON Batsim profiles file')
parser.add_argument('result_dir',
                    help='The result directory to put the result and find the hostname')
parser.add_argument('outputJSON',
                    help='The output JSON OAR gantt file. It will be put in the result_dir')

args = parser.parse_args()

# parse the workload to get jobs
json_data = json.load(args.inputJSON)
assert('profiles' in json_data), ("Invalid input file: It must contains a"
                                  "'profiles' map")

# get job list sorted on the submission time
# NOT NECESSARY using sche class
# jobs = sorted(json_data['Jobs'], key=lambda job: job['subtime'])
jobs = json_data['jobs']
profiles = json_data['profiles']

# run the jobs
begin = datetime.now()

scheduler = sched.scheduler(time.time, time.sleep)
for job in jobs:
    # get command
    cmd = profiles[job['profile']]['command']
    scheduler.enter(job['subtime'],
                    0,
                    do_oar_submission,
                    kwargs={'command': cmd,
                            'walltime': job['walltime'],
                            'resources': job['res'],
                            'hostfile_dir': args.result_dir})
    scheduler.run()

while True:
    process = Popen(["oarstat"], stdout=PIPE)
    (output, err) = process.communicate()
    if not output:
        break
    time.sleep(1)

end = datetime.now()

get_scheduling_results(args.result_dir + '/' + args.outputJSON)
