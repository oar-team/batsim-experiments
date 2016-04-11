#!/usr/bin/python3

'''
This script reads an OAR result JSON file and transforms it into a Batsim CSV jobs result file.
'''

import argparse
import math
import sys
import json
import datetime

# Program parameters parsing
parser = argparse.ArgumentParser(description='Reads an OAR result JSON file and transforms it into a Batsim CSV jobs result file.')
parser.add_argument('inputJSON', type=argparse.FileType('r'), help='The input OAR result detailed Gantt JSON file')
parser.add_argument('outputJSON', type=argparse.FileType('w'), help='The output JSON Batsim workload file')
parser.add_argument('-r', '--reduceSubmitTimes', action='store_true', help='If set, job submission times are translated s.t. min(submission_time) = 0')
parser.add_argument('-i', '--indent', type=int, default=None, help='If set to a non-negative integer, then JSON array elements and object members will be pretty-printed with that indent level. An indent level of 0, or negative, will only insert newlines. The default value (None) selects the most compact representation.')
parser.set_defaults(reduceSubmitTimes=False)

args = parser.parse_args()

# Reading the input file
input_json_data = json.load(args.inputJSON)
assert('jobs' in input_json_data), "No 'jobs' in {}".format(args.inputJSON.name)
jobs = input_json_data['jobs']

assigned_resources = set()

# Computing the offset for submission time
submission_time_offset = float('inf')
if args.reduceSubmitTimes:
    for job in jobs:
        job_submission_time = float(jobs[job]['submissionTime'])
        submission_time_offset = min(submission_time_offset, job_submission_time)

# Traversing the input file to create the output jobs and profiles
output_jobs = list()
output_profiles = dict()
for job in jobs:
    job_id = int(job)
    job_submission_time = float(jobs[job]['submissionTime']) - submission_time_offset
    job_start_time = float(jobs[job]['startTime']) - submission_time_offset
    job_stop_time = float(jobs[job]['stopTime']) - submission_time_offset
    job_resources = [int(x) for x in jobs[job]['assigned_resources']]
    job_size = int(len(job_resources))
    job_walltime = float(jobs[job]['walltime'])
    job_runtime = job_stop_time - job_start_time

    for res in job_resources:
        assigned_resources.add(res)

    output_profiles[str(job_id)] = {"type": "delay", "delay": job_runtime}
    output_jobs.append({"profile": str(job_id),
                        "res": job_size,
                        "id": job_id,
                        "subtime": job_submission_time,
                        "walltime": job_walltime
                    })


output_data = {'command' : ' '.join(sys.argv[:]),
               'date' : datetime.datetime.now().isoformat(' '),
               'description' : 'This workload has been generated from an OAR gantt output',
               'nb_res' : len(assigned_resources),
               'jobs' : output_jobs,
               'profiles' : output_profiles
    }

try:
    json.dump(output_data, args.outputJSON, indent=args.indent, sort_keys=True)
except IOError:
    print('Cannot write file', args.outputJSON)
    raise

