#!/usr/bin/python3

'''
This script reads an OAR result JSON file and transforms it into a Batsim CSV jobs result file.
'''

import argparse
import math
import csv
import json

# Program parameters parsing
parser = argparse.ArgumentParser(description='Reads an OAR result JSON file and transforms it into a Batsim CSV jobs result file.')
parser.add_argument('inputJSON', type=argparse.FileType('r'), help='The input JSON profiles description file')
parser.add_argument('outputCSV', type=argparse.FileType('w'), help='The output CSV Batsim jobs file')

args = parser.parse_args()

# Reading the input file
input_json_data = json.load(args.inputJSON)
assert('jobs' in input_json_data), "No 'jobs' in {}".format(args.inputJSON.name)
jobs = input_json_data['jobs']

# Traversing the input file to create the output jobs
output_jobs = list()
for job in jobs:
    job_id = int(job)
    job_submission_time = float(jobs[job]['submission_time'])
    job_start_time = float(jobs[job]['start_time'])
    job_stop_time = float(jobs[job]['stop_time'])
    job_resources = [int(x) for x in jobs[job]['resources']]
    job_resources_string = ' '.join([str(x) for x in jobs[job]['resources']])
    job_size = len(job_resources)
    job_walltime = float(jobs[job]['walltime'])
    job_state = str(jobs[job]['state'])
    job_consumed_energy = -1

    job_runtime = job_stop_time - job_start_time
    job_waiting_time = job_start_time - job_submission_time
    job_turnaround_time = job_stop_time - job_submission_time
    job_stretch = job_turnaround_time / job_runtime

    job_success = 0
    if job_state == 'Terminated':
        job_success = 1

    output_jobs.append({'jobID':job_id,
                        'submission_time':job_submission_time,
                        'requested_number_of_processors':job_size,
                        'requested_time':job_walltime,
                        'success':job_success,
                        'starting_time':job_start_time,
                        'execution_time':job_runtime,
                        'finish_time':job_stop_time,
                        'waiting_time':job_waiting_time,
                        'turnaround_time':job_turnaround_time,
                        'stretch':job_stretch,
                        'consumed_energy':job_consumed_energy,
                        'allocated_processors':job_resources_string})

# Writing the output file
writer = csv.DictWriter(args.outputCSV, fieldnames=['jobID',
                                                    'submission_time',
                                                    'requested_number_of_processors',
                                                    'requested_time',
                                                    'success',
                                                    'starting_time',
                                                    'execution_time',
                                                    'finish_time',
                                                    'waiting_time',
                                                    'turnaround_time',
                                                    'stretch',
                                                    'consumed_energy',
                                                    'allocated_processors'])

writer.writeheader()
for output_job in output_jobs:
    writer.writerow(output_job)


