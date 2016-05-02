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
parser.add_argument('inputJSON', type=argparse.FileType('r'), help='The input OAR result JSON file')
parser.add_argument('outputCSV', type=argparse.FileType('w'), help='The output CSV Batsim jobs file')
parser.add_argument('-m', '--jobIDMappingCSV', type=argparse.FileType('r'), default=None, help='The optionnal CSV mapping of job IDs between those of Batsim and those of OAR')
parser.add_argument('-r', '--reduceSubmitTimes', action='store_true', help='If set, job submission times are translated s.t. min(submission_time) = 0')
parser.add_argument('-z', '--reduceMachineNumbers', action='store_true', help='If set, the machine numbers are translated such that the new minimum is 0')
parser.set_defaults(reduceSubmitTimes=False)

args = parser.parse_args()

# Reading the job_id mappingi
if args.jobIDMappingCSV != None:
    reader = csv.DictReader(args.jobIDMappingCSV)
    assert('batsim_id' in reader.fieldnames), "No 'batsim_id' field in {}".format(args.jobIDMappingCSV.name)
    assert('oar_id' in reader.fieldnames), "No 'oar_id' field in {}".format(args.jobIDMappingCSV.name)

    oar_id_to_batsim_id = {}
    batsim_id_to_oar_id = {}

    for row in reader:
        oar_id = int(row['oar_id'])
        batsim_id = int(row['batsim_id'])
        oar_id_to_batsim_id[oar_id] = batsim_id
    batsim_id_to_oar_id[batsim_id] = oar_id

# Reading the input file
input_json_data = json.load(args.inputJSON)
assert('jobs' in input_json_data), "No 'jobs' in {}".format(args.inputJSON.name)
jobs = input_json_data['jobs']

# Computing the offset for submission time
submission_time_offset = float('inf')
if args.reduceSubmitTimes:
    for job in jobs:
        job_submission_time = float(jobs[job]['submission_time'])
        submission_time_offset = min(submission_time_offset, job_submission_time)
else:
    submission_time_offset = 0

# Traversing the input file to find the minimum resource_id
min_resource_id = 0
if args.reduceMachineNumbers:
    resource_ids = set()
    for job in jobs:
        job_resources = [int(x) for x in jobs[job]['resources']]
        for resource_id in job_resources:
            resource_ids.add(resource_id)
    min_resource_id = min(resource_ids)

# Traversing the input file to create the output jobs
output_jobs = list()
for job in jobs:
    if args.jobIDMappingCSV != None:
        job_id = oar_id_to_batsim_id[int(job)]
    else:
        job_id = int(job)
    job_submission_time = float(jobs[job]['submission_time']) - submission_time_offset
    job_start_time = float(jobs[job]['start_time']) - submission_time_offset
    job_stop_time = float(jobs[job]['stop_time']) - submission_time_offset
    job_resources = [int(x) - min_resource_id for x in jobs[job]['resources']]
    job_resources_string = ' '.join([str(x) for x in job_resources])
    job_size = int(len(job_resources))
    job_walltime = float(jobs[job]['walltime'])
    job_state = str(jobs[job]['state'])
    job_consumed_energy = int(-1)

    job_runtime = float(job_stop_time - job_start_time)
    job_waiting_time = float(job_start_time - job_submission_time)
    job_turnaround_time = float(job_stop_time - job_submission_time)
    job_stretch = float(job_turnaround_time / job_runtime)

    job_success = 0
    if job_state == 'Terminated':
        job_success = 1
    job_success = int(job_success)

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


