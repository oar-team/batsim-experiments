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
import datetime

# Program parameters parsing
parser = argparse.ArgumentParser(description='Reads an OAR Gantt JSON file containing and extracts information about the jobs it contains')
parser.add_argument('inputJSON', type=argparse.FileType('r'), help='The input JSON OAR Gannt file')

args = parser.parse_args()

input_json_data = json.load(args.inputJSON)
assert('jobs' in input_json_data), "No 'jobs' in {}".format(args.inputJSON)

jobs = input_json_data['jobs']

finished_jobs = []
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
        finished_jobs.append(job)
    elif job_state == 'Error':
        error_jobs.append(job)
    else:
        print("{}: {}".format(job_id, job_state))

finished_jobs.sort()
error_jobs.sort()
timeout_jobs.sort()

print('Finished jobs: {}, [{}]'.format(len(finished_jobs), ','.join(finished_jobs)))
print()
print('Error jobs: {}, [{}]'.format(len(error_jobs), ','.join(error_jobs)))
print()
print('Timeout jobs: {}, [{}]'.format(len(error_jobs), ','.join(error_jobs)))

print('Timeout jobs that are not error:', set(timeout_jobs) - set(error_jobs))
print('Error jobs that are not timeout:', set(error_jobs) - set(timeout_jobs))
