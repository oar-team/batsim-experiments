#!/usr/bin/python3

'''
This script reads a JSON file containing profiles and generates
a workload from it. An example is given in "profiles_example.json"

The profiles must respect these constraints:
    - They must be Batsim-valid
    - They must have additional fields:
        - a "command" field, used to know how the job was run
        - a "np" fiel, used to know on which number of processors the command was run
        - a "runtime" field, used to know the execution time of the run command


'''

import argparse
import math
import sys
import random
import json
import datetime

# Program parameters parsing
parser = argparse.ArgumentParser(description='Reads a JSON profiles description file and generates a JSON workload (used by Batsim) from it')
parser.add_argument('inputJSON', type=argparse.FileType('r'), help='The input JSON profiles description file')
parser.add_argument('outputJSON', type=argparse.FileType('w'), help='The output JSON workload file')
parser.add_argument('resourcesNumber', type=int, help='The number of resources in the platform')
parser.add_argument('-rs', '--random_seed', type=int, default=None, help='The random seed')
parser.add_argument('-jn', '--job_number', type=int, default=300, help='The number of jobs to generate')
parser.add_argument('-sjp', '--serial_job_probability', type=float, default=0.25, help="The probability of a job being serial (executed on a single resource)")
parser.add_argument('-mu', '--job_log_size_mu', type=float, default=1, help="The mu used in the lognormal distribution used to generate job sizes")
parser.add_argument('-sigma', '--job_log_size_sigma', type=float, default=0.5, help="The sigma used in the lognormal distribution used to generate job sizes")
parser.add_argument('-lambda', '--job_iarrival_lambda', type=float, default=5, help="The lambda (scale parameter) used in the Weibull distribution used to generate job interarrival times")
parser.add_argument('-k', '--job_iarrival_k', type=float, default=10, help="The lambda (shape parameter) used in the Weibull distribution used to generate job interarrival times")
parser.add_argument('-i', '--indent', type=int, default=None, help='If set to a non-negative integer, then JSON array elements and object members will be pretty-printed with that indent level. An indent level of 0, or negative, will only insert newlines. The default value (None) selects the most compact representation.')
parser.add_argument('-mp', '--maximum_power_of_two', type=int, default=5, help="The maximum allowed job size. The default (5) means the jobs exceeding 2^5=32 resources are ignored")

args = parser.parse_args()

# Constants
#args.maximum_power_of_two = 5

# Input check
assert(args.job_number > 0), "The number of jobs must be strictly positive (read {})".format(args.job_number)
assert(args.serial_job_probability >= 0 and args.serial_job_probability <= 1), "The probability of a job being serial must be between 0 and 1 (read {})".format(args.serial_job_probability)

# Entry point
if args.random_seed and args.random_seed > 0:
    random.seed(args.random_seed)

# Profile loading
profiles = {}
try:
    input_json_data = json.load(args.inputJSON)
    assert("profiles" in input_json_data), "No 'profiles' in {}".format(input_json_data)
    profiles = input_json_data["profiles"]
    for prof in profiles:
        if "command" not in profiles[prof]:
            print("Warning: profile {} is ignored because he has no 'command' field".format(prof))
            del profiles[prof]
        elif "np" not in profiles[prof]:
            print("Warning: profile {} is ignored be cause he has no 'np' field".format(prof))
            del profiles[prof]
        elif "runtime" not in profiles[prof]:
            print("Warning: profile {} is ignored be cause he has no 'runtime' field".format(prof))
            del profiles[prof]
except IOError:
    print('Cannot read file', args.inputJSON)
    raise

# Let the profiles be structured by their size. If p is in sprofiles[i], its size is 2**i
sprofiles = []
for i in range(args.maximum_power_of_two + 1):
    sprofiles.append([])

for prof in profiles:
    #prof = profiles[prof]
    i = math.log(profiles[prof]["np"], 2)
    if (i == int(i)):
        if (i >= 0) and (i <= args.maximum_power_of_two):
            i = int(i)
            sprofiles[i].append(prof)
        else:
            print("Warning: profile {} is ignored because its size ({}) is not between 0 and {}".format(prof, profiles[prof]['np'], 2**args.maximum_power_of_two))
    else:
        print("Warning: profile {} is ignored because its size ({}) is not a power of 2".format(prof, profiles[prof]['np']))

# Let us make sure that profiles exist for all i
for i in range(args.maximum_power_of_two + 1):
    assert(len(sprofiles[i]) > 0), "There is no profile corresponding to job_size={}, aborting.".format(2**i)

# Let the sprofiles be sorted by some criteria to ensure output determinism since the JSON library does not seem to be deterministic
for sublist in sprofiles:
    sublist.sort()

# Workload generation
workload = []

# For each job that we want to generate
release_date = 0
for job_id in range(args.job_number):
    # First, let the job size be determined
    job_size = -1
    job_size_base = -1
    # Let us determine if the job is parallel or not
    if random.random() < args.serial_job_probability:
        job_size_base = 0
    else:
        # The job is not serial, it is then a power of 2.
        # Let us determine that power with a lognormal distribution.
        # cf. page 505 of "Workload modeling for performance evaluation", Dror Feitelson
        while (job_size_base < 1) or (job_size_base > args.maximum_power_of_two):
            job_size_base = random.lognormvariate(args.job_log_size_mu, args.job_log_size_sigma)
            job_size_base = round(job_size_base)
            job_size_base = abs(job_size_base)

    job_size = 2**job_size_base

    # Now that we know the job size, we can select a profile uniformly among
    # those which have the right size
    idx = random.randint(0, len(sprofiles[job_size_base])-1)
    job_profile = sprofiles[job_size_base][idx];

    # The interarrival times are supposed to fit a Weibull distribution
    # cf. page 502 of "Workload modeling for performance evaluation", Dror Feitelson
    job_release_date = release_date
    release_date = release_date + random.weibullvariate(args.job_iarrival_lambda, args.job_iarrival_k)

    workload.append((job_id, job_size, job_profile, release_date)) #fixme: use job_release_date

#df = pandas.DataFrame(data = workload, columns=['id','size','profile','release_date'])
#df.to_csv('jobs.csv',index=False,header=True)
#print(workload)

# Json generation
djobs = []
for (job_id, job_size, job_profile, release_date) in workload:
    djobs.append({'id':job_id, 'subtime':release_date , 'walltime':max(60,profiles[job_profile]["runtime"]*1.5), 'res':job_size, 'profile': job_profile})

json_data = {
    #'version':version,
    'command':' '.join(sys.argv[:]),
    'date': datetime.datetime.now().isoformat(' '),
    'description':'this workload had been automatically generated',
    'nb_res': args.resourcesNumber,
    'jobs':djobs,
    'profiles':profiles
    }

if 'description' in input_json_data:
    json_data['profiles_description'] = input_json_data['description']

try:
    json.dump(json_data, args.outputJSON, indent=args.indent, sort_keys=True)
except IOError:
    print('Cannot write file', args.outputJSON)
    raise
