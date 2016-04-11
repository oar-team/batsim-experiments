#!/usr/bin/python3

'''
This script modifies the profiles of a Batsim workload to add a noise on the execution time of each profile.
'''

import argparse
import math
import sys
import random
import pandas
import json
import os
import datetime

parser = argparse.ArgumentParser(description='Modifies the profiles of a Batsim workload to add a noise on the execution time of each profile')
parser.add_argument('inputJSON', type=argparse.FileType('r'), help='The input JSON workload file')
parser.add_argument('--runtime_noise_mu', type=float, default=0.5, help='The mean of the gaussian noise')
parser.add_argument('--runtime_noise_sigma', type=float, default=0.7, help='The standard deviation of the gaussian noise')
parser.add_argument('--subtime_noise_mu', type=float, default=0.4, help='The mean of the gaussian noise')
parser.add_argument('--subtime_noise_sigma', type=float, default=0.18, help='The standard deviation of the gaussian noise')
parser.add_argument('--random_seed', type=int, default=None, help='The random seed used to generate the noise')
parser.add_argument('outputJSON', type=argparse.FileType('w'), help='The output JSON workload file')
parser.add_argument('-i', '--indent', type=int, default=None, help='If set to a non-negative integer, then JSON array elements and object members will be pretty-printed with that indent level. An indent level of 0, or negative, will only insert newlines. The default value (None) selects the most compact representation.')

args = parser.parse_args()

if args.random_seed:
    random.seed(args.random_seed)

json_data = json.load(args.inputJSON)
assert('profiles' in json_data), "Invalid input file: there must be a 'profiles' map in it"

nb_modified = 0
nb_traversed = 0

for profile in json_data['profiles']:
    if json_data['profiles'][profile]['type'] == 'delay':
        json_data['profiles'][profile]['delay'] = float(json_data['profiles'][profile]['delay']) + random.gauss(args.runtime_noise_mu, args.runtime_noise_sigma)
        nb_modified += 1
    nb_traversed += 1

if nb_modified != nb_traversed:
    print("Warning: out of {} profiles, only {} have been modified (the other ones are probably not delay profiles)".format(nb_traversed, nb_modified))

assert('jobs' in json_data), "Invalid input file: there must be a 'jobs' map in it"
jobs = json_data['jobs']
for job in jobs:
    job['subtime'] = float(job['subtime']) + random.gauss(args.subtime_noise_mu, args.subtime_noise_mu)

json_data['jobs'] = jobs

try:
    json.dump(json_data, args.outputJSON, indent=args.indent, sort_keys=True)
    args.outputJSON.close()
except IOError:
    print("Cannot write file ", args.outputJSON)
