#!/usr/bin/python3

'''
This script reads an OAR Gantt JSON file and extracts
information about the jobs it contains

'''

import argparse
import math
import sys
import random
import pandas
import json
import os
import datetime

# Program parameters parsing
parser = argparse.ArgumentParser(description='Reads an OAR Gantt JSON file containing and extracts information about the jobs it contains')
parser.add_argument('inputJSON', type=argparse.FileType('r'), help='The input JSON OAR Gannt file')

args = parser.parse_args()

input_json_data = json.load(args.inputJSON)
assert('jobs' in input_json_data), "No 'jobs' in {}".format(args.inputJSON)

jobs = input_json_data['jobs']

terminated_jobs = []
error_jobs = []
timeout_jobs = []

for job in jobs:
    job_id = int(job)
    job_state = jobs[job]['state']
    job_limit_stop_time = float(jobs[job]['limit_stop_time'])
    job_stop_time = float(jobs[job]['stop_time'])

    if job_stop_time >= job_limit_stop_time:
        timeout_jobs.append(job)

    if job_state == 'Terminated':
        terminated_jobs.append(job)
    elif job_state == 'Error':
        error_jobs.append(job)
    else:
        print("{}: {}".format(job_id, job_state))

terminated_jobs.sort()
error_jobs.sort()
timeout_jobs.sort()

terminated_jobs_no_stderr = []
# Detect terminated nodes with no stderr
for job in terminated_jobs:
    filename = 'OAR{}.stderr'.format(job)
    if os.stat(filename).st_size == 0:
        terminated_jobs_no_stderr.append(job)

print('Finished jobs no stderr: {}, [{}]'.format(len(terminated_jobs_no_stderr), ','.join(terminated_jobs_no_stderr)))
print()

terminated_jobs_not_really_finished = []
for job in terminated_jobs:
    filename = 'OAR{}.stdout'.format(job)
    with open(filename, 'r') as file:
        content = file.read()
        if content.find('Time in seconds') == -1:
            terminated_jobs_not_really_finished.append(job)

terminated_jobs_no_stderr.sort()
terminated_jobs_not_really_finished.sort()
terminated_jobs_finished = list(set(terminated_jobs) - set(terminated_jobs_not_really_finished))
terminated_finished_jobs_with_stderr = list(set(terminated_jobs_finished) - set(terminated_jobs_no_stderr))

print('Terminated jobs: {}, [{}]'.format(len(terminated_jobs), ','.join(terminated_jobs)))
print()
print('Error jobs: {}, [{}]'.format(len(error_jobs), ','.join(error_jobs)))
print()
print('Timeout jobs: {}, [{}]'.format(len(error_jobs), ','.join(error_jobs)))

print()
print('Timeout jobs that are not error: {}'.format(set(timeout_jobs) - set(error_jobs)))
print('Error jobs that are not timeout: {}'.format(set(error_jobs) - set(timeout_jobs)))

print()
print('Terminated jobs that have no stderr: {}, [{}]'.format(len(terminated_jobs_no_stderr), ','.join(terminated_jobs_no_stderr)))
print('Terminated jobs not really finished: {}, [{}]'.format(len(terminated_jobs_not_really_finished), ','.join(terminated_jobs_not_really_finished)))

print('Terminated finished jobs: {}, [{}]'.format(len(terminated_jobs_finished), ','.join(terminated_jobs_finished)))
print('Terminated finished jobs that have a stderr: {}, [{}]'.format(len(terminated_finished_jobs_with_stderr), ','.join(terminated_finished_jobs_with_stderr)))

#print('\n'.join(['{}: [{}]'.format(ok_job, ','.join([str(r) for r in jobs[ok_job]['resources']])) for ok_job in terminated_jobs_no_stderr]))

#for ok_job in terminated_jobs_no_stderr:
#    res = '{}: [{}]'.format(ok_job, ','.join([str(r) for r in jobs[ok_job]['resources']]))

