#!/usr/bin/python3

'''
This script reads a the jobs of one workload and the profiles of another workload
and merges the two of them
'''

import argparse
import math
import sys
import random
import json
import datetime

# Program parameters parsing
parser = argparse.ArgumentParser(description='This script reads a the jobs of one workload and the profiles of another workload and merges the two of them')
parser.add_argument('inputProfilesWorkloadJSON', type=argparse.FileType('r'), help='The input JSON profiles description file')
parser.add_argument('inputJobsWorkloadJSON', type=argparse.FileType('r'), help='The input JSON jobs description file')
parser.add_argument('outputWorkloadJSON', type=argparse.FileType('w'), help="The output JSON workload file")
parser.add_argument('resourcesNumber', type=int, help='The number of resources in the platform')
parser.add_argument('-i', '--indent', type=int, default=None, help='If set to a non-negative integer, then JSON array elements and object members will be pretty-printed with that indent level. An indent level of 0, or negative, will only insert newlines. The default value (None) selects the most compact representation.')

args = parser.parse_args()

# Reading input
input_jobs_workload_json = json.load(args.inputJobsWorkloadJSON)
input_profiles_workload_json = json.load(args.inputProfilesWorkloadJSON)

assert('jobs' in input_jobs_workload_json)
assert('profiles' in input_profiles_workload_json)

# Mapping jobs to profiles
jobs = input_jobs_workload_json['jobs']
profiles = input_profiles_workload_json['profiles']

for job in jobs:
    job_profile = job['profile']

    if not job_profile in profiles:
        job_profile_modified = job_profile.replace('delay_', '', 1)

        if not job_profile_modified in profiles:
            error_str = "Cannot find job_profile '{}' (nor '{}') in file '{}'".format(job_profile, job_profile_modified, args.inputProfilesWorkloadJSON.name)
            print(error_str)
            raise runtimeError(error_str)
        else:
            job['profile'] = job_profile_modified

# Writing output
# Json generation
djobs = []
json_data = {
    'command':' '.join(sys.argv[:]),
    'date': datetime.datetime.now().isoformat(' '),
    'description':'this workload had been automatically generated',
    'nb_res': args.resourcesNumber,
    'jobs':jobs,
    'profiles':profiles
    }

try:
    json.dump(json_data, args.outputWorkloadJSON, indent=args.indent, sort_keys=True)
except IOError:
    print('Cannot write file', args.outputWorkloadJSON)
    raise
