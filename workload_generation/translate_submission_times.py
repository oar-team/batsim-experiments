#!/usr/bin/python3

'''
This script reads a Batsim CSV workload and translates job submission times such that min(job submission time) = 0
'''

import argparse
import math
import sys
import json
import datetime

# Program parameters parsing
parser = argparse.ArgumentParser(description='Reads a Batsim CSV workload and translates job submission times such that min(job submission time) = 0')
parser.add_argument('inputJSON', type=argparse.FileType('r+'), help='The input JSON Batsim workload file')
parser.add_argument('-w', '--forceIntegerWalltimes', action="store_true", help="If set, job walltimes are put into integer via ceil")
parser.add_argument('-i', '--indent', type=int, default=None, help='If set to a non-negative integer, then JSON array elements and object members will be pretty-printed with that indent level. An indent level of 0, or negative, will only insert newlines. The default value (None) selects the most compact representation.')
parser.set_defaults(reduceSubmitTimes=False)

args = parser.parse_args()

# Reading the input file
input_json_data = json.load(args.inputJSON)
assert('jobs' in input_json_data), "No 'jobs' in {}".format(args.inputJSON.name)
jobs = input_json_data['jobs']
profiles = input_json_data['profiles']

# Computing the offset for submission time
submission_time_offset = float('inf')
for job in jobs:
    job_submission_time = float(job['subtime'])
    submission_time_offset = min(submission_time_offset, job_submission_time)

assert(math.isfinite(submission_time_offset)), "Non finite submission time offset ({})".format(submission_time_offset)

# Update submission time
for job in jobs:
    job_submission_time = float(job['subtime']) - submission_time_offset

    job['subtime'] = job_submission_time

    if args.forceIntegerWalltimes:
        job['walltime'] = int(math.ceil(job['walltime']))

output_data = {'command' : ' '.join(sys.argv[:]),
               'date' : datetime.datetime.now().isoformat(' '),
               'description' : 'This workload has been translated (min(submission time) = 0)',
               'nb_res' : input_json_data['nb_res'],
               'jobs' : jobs,
               'profiles' : profiles
    }

# Erase file content
args.inputJSON.seek(0)
args.inputJSON.truncate()

# Write new content
try:
    json.dump(output_data, args.inputJSON, indent=args.indent, sort_keys=True)
except IOError:
    print('Cannot write file', args.inputJSON)
    raise

