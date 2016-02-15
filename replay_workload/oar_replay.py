#!/usr/bin/env python3
'''
This script is taking a Batsim profile as input and replay the profile
using the provided commands.
'''
import argparse
import json
import sched
import time
import execo
from datetime import datetime


def do_oar_submission(command, walltime, resources):
    hms_time = datetime.timedelta(secounds=walltime)
    oar_time = ":".join(hms_time.hours, hms_time.minutes,
                        hms_time.secounds)
    execo.Process('oarsub -l \\nodes=' + resources + ',walltime=' +
                  oar_time + ' ' + cmd)


def get_scheduling_results():
    fmt = '%Y-%m-%d %X'
    execo.Process('oarstat -J --gantt "' + begin.strftime(fmt) + ',' +
                  end.strftime(fmt) + '"')
    # TODO add handler

parser = argparse.ArgumentParser(description='Replay Batsim profile using'
                                             'OAR submitions')
parser.add_argument('inputJSON',
                    type=argparse.FileType('r'),
                    help='The input JSON Batsim profiles file')

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
                            'resources_number': job['res']})
    scheduler.run()

end = datetime.now()

get_scheduling_results()
