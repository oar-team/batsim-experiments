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

for job in jobs:
    job_id = int(job)
    state = jobs[job]['state']

    if state == 'Terminated':
        finished_jobs.append(job)
    elif state == 'Error':
        error_jobs.append(job)
    else:
        print("{}: {}".format(job_id, state))

print('Finished jobs: {}, [{}]'.format(len(finished_jobs), ','.join(finished_jobs)))
print()
print('Error jobs: {}, [{}]'.format(len(error_jobs), ','.join(error_jobs)))
