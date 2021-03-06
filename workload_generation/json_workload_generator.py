#!/usr/bin/python3

'''
This script reads a JSON file containing profiles and generates
a workload from it. An example is given in "profiles_example.json"

The profiles must respect these constraints:
  - They must be Batsim-valid
  - They must have additional fields:
    - a "command" field: to know how the job was run
    - a "np" field: to know on which number of processors the command was run
    - a "runtime" field: to know the execution time of the run command

Usage:
    json_workload_generator.py profiles_example.json my_workload.json 200
'''

import argparse
import math
import sys
import random
import json
import datetime


def roundup(x, round_by):
    return round(x) if x % round_by == 0 else round(x + round_by - x %
                                                    round_by)


def generate_walltime(runtime, factor=1.3):
    """
    Generate a walltime value that fit natural boundaries regarding job
    size. All walltime values are factor of the runtime.
    """
    if runtime < 60 * 10:
        return roundup(runtime * factor, 100)
    if runtime < 60 * 60:
        return roundup(runtime * factor, 600)
    if runtime < 60 * 60 * 24:
        return roundup(runtime * factor, 3600)


if __name__ == "__main__":

    # Program parameters parsing
    parser = argparse.ArgumentParser(
        description='Reads a JSON profiles description file and generates a '
                    'JSON workload (used by Batsim) from it')
    parser.add_argument(
        'inputJSON', type=argparse.FileType('r'),
        help='The input JSON profiles description file')
    parser.add_argument(
        'outputJSON', type=argparse.FileType('w'),
        help='The output JSON workload file')
    parser.add_argument(
        'resourcesNumber', type=int,
        help='The number of resources in the platform')
    parser.add_argument(
        '-rs', '--random_seed', type=int, default=None,
        help='The random seed')
    parser.add_argument(
        '-jn', '--job_number', type=int, default=300,
        help='The number of jobs to generate')
    parser.add_argument(
        '-sjp', '--serial_job_probability', type=float,
        default=0.25,
        help="The probability of a job being serial "
             "(executed on a single resource)")
    parser.add_argument(
        '-mu', '--job_log_size_mu', type=float, default=1, help="The mu "
        "used in the lognormal distribution used to generate job sizes")
    parser.add_argument(
        '-sigma', '--job_log_size_sigma', type=float,
        default=0.5,
        help="The sigma used in the lognormal distribution used to generate "
             "job sizes")
    parser.add_argument(
        '-lambda', '--job_iarrival_lambda', type=float,
        default=5,
        help="The lambda (scale parameter) used in the Weibull distribution "
             "used to generate job interarrival times")
    parser.add_argument(
        '-k', '--job_iarrival_k', type=float, default=10,
        help="The lambda (shape parameter) used in the Weibull distribution "
             "used to generate job interarrival times")
    parser.add_argument(
        '-i', '--indent', type=int, default=None,
        help="If set to a non-negative integer, then JSON array elements and "
             "object members will be pretty-printed with that indent level. "
             "An indent level of 0, or negative, will only insert newlines. "
             "The default value (None) selects the most compact "
             "representation.")
    parser.add_argument(
        '-mp', '--maximum_power_of_two', type=int, default=5,
        help="The maximum allowed job size. The default (5) means the jobs "
             "exceeding 2^5=32 resources are ignored")
    parser.add_argument(
        '--maximum_job_length', type=float, default=None,
        help='Only jobs with a runtime lesser than this value are kept')

    args = parser.parse_args()

    # Input check
    if args.job_number <= 0:
        raise ValueError("The number of jobs must be strictly positive "
                         "(read {})".format(args.job_number))
    if 0 >= args.serial_job_probability <= 1:
        raise ValueError("The probability of a job being serial must be "
                         "between 0 and 1 (read {})".format(
                             args.serial_job_probability))

    # Entry point
    if (args.random_seed is not None) and args.random_seed >= 0:
        random.seed(args.random_seed)

    # Profile loading
    profiles = {}
    try:
        input_json_data = json.load(args.inputJSON)
        if "profiles" not in input_json_data:
            raise ValueError("No 'profiles' in {}".format(input_json_data))
        profiles = input_json_data["profiles"]
        for prof in profiles:
            if "command" not in profiles[prof]:
                print("Warning: profile {} is ignored because he has no "
                      "'command' field".format(prof))
                del profiles[prof]
            elif "np" not in profiles[prof]:
                print("Warning: profile {} is ignored be cause he has no 'np' "
                      "field".format(prof))
                del profiles[prof]
            elif "runtime" not in profiles[prof]:
                print("Warning: profile {} is ignored be cause he has no "
                      "'runtime' field".format(prof))
                del profiles[prof]
    except IOError:
        print('Cannot read file', args.inputJSON)
        raise

    # Let the profiles be structured by their size. If p is in sprofiles[i],
    # its size is 2**i
    sprofiles = []
    for i in range(args.maximum_power_of_two + 1):
        sprofiles.append([])

    nb_ignored_because_of_length = 0

    for prof in profiles:
        i = math.log(profiles[prof]["np"], 2)
        if (i == int(i)):
            if (i >= 0) and (i <= args.maximum_power_of_two):
                if (args.maximum_job_length is None or
                    ((args.maximum_job_length is not None) and
                     (float(profiles[prof]['runtime']) <=
                      args.maximum_job_length))):
                    i = int(i)
                    sprofiles[i].append(prof)
                else:
                    nb_ignored_because_of_length += 1
            else:
                print("Warning: profile {} is ignored because its size ({}) "
                      "is not between 0 and {}".format(
                          prof, profiles[prof]['np'],
                          2**args.maximum_power_of_two))
        else:
            print("Warning: profile {} is ignored because its size ({}) is not"
                  " a power of 2".format(prof, profiles[prof]['np']))

    if nb_ignored_because_of_length > 0:
        print("{} jobs have been ignored because of maximum job length "
              "{}".format(nb_ignored_because_of_length,
                          args.maximum_job_length))

    # Let us make sure that profiles exist for all i
    for i in range(args.maximum_power_of_two + 1):
        if len(sprofiles[i]) <= 0:
            raise ValueError(
                "There is no profile corresponding to job_size={},"
                " aborting.".format(2**i))

    # Let the sprofiles be sorted by some criteria to ensure output
    # determinism since the JSON library does not seem to be deterministic
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
            # cf. page 505 of "Workload modeling for performance evaluation",
            # Dror Feitelson
            while (job_size_base < 1
                   or job_size_base > args.maximum_power_of_two):
                job_size_base = random.lognormvariate(
                    args.job_log_size_mu, args.job_log_size_sigma)
                job_size_base = round(job_size_base)
                job_size_base = abs(job_size_base)

        job_size = 2**job_size_base

        # Now that we know the job size, we can select a profile uniformly
        # among those which have the right size
        idx = random.randint(0, len(sprofiles[job_size_base]) - 1)
        job_profile = sprofiles[job_size_base][idx]

        # The interarrival times are supposed to fit a Weibull distribution
        # cf. page 502 of "Workload modeling for performance evaluation",
        # form Dror Feitelson
        job_release_date = release_date
        release_date = release_date + random.weibullvariate(
            args.job_iarrival_lambda, args.job_iarrival_k)
        # FIXME: use job_release_date
        workload.append(
            (job_id, job_size, job_profile, release_date))

    # Json generation
    djobs = []
    for (job_id, job_size, job_profile, release_date) in workload:
        djobs.append({'id': job_id,
                      'subtime': release_date,
                      'walltime': generate_walltime(
                          profiles[job_profile]['runtime']),
                      'res': job_size,
                      'profile': job_profile})

    json_data = {
        'command': ' '.join(sys.argv[:]),
        'date':  datetime.datetime.now().isoformat(' '),
        'description': str(args),
        'nb_res':  args.resourcesNumber,
        'jobs': djobs,
        'profiles': profiles
    }

    if 'description' in input_json_data:
        json_data['profiles_description'] = input_json_data['description']

    try:
        json.dump(json_data,
                  args.outputJSON,
                  indent=args.indent,
                  sort_keys=True)
    except IOError:
        print('Cannot write file', args.outputJSON)
        raise
