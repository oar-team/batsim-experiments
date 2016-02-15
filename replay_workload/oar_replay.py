#!/usr/bin/env python3
'''
This script is taking a Batsim profile as input and replay the profile
using the provided commands.
'''
import argparse
import json
import sched
import time
from subprocess import call
from datetime import datetime, timedelta


def do_oar_submission(command, walltime, resources):
    hms_time = timedelta(seconds=walltime)
    oar_time = str(hms_time).split('.')[0]
    oar_cmd = ('oarsub -l \\nodes=' + str(resources) + ',walltime=' +
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
parser.add_argument('outputJSON',
                    help='The output JSON OAR gantt file')

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
                            'resources': job['res']})
    scheduler.run()

end = datetime.now()

get_scheduling_results(args.outputJSON)
