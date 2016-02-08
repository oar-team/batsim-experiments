#!/usr/bin/python3

'''
This script reads a SimGrid time-independent trace (TIT) file corresponding
to one job execution and transforms it in a Batsim JSON profile, which is added
in the output JSON file.
'''

import argparse
import math
import sys
import random
import pandas
import json
import os
import datetime

parser = argparse.ArgumentParser(description='Reads a SimGrid time-independent trace (TIT) file corresponding to one job execution and transforms it into a Batsim JSON profile. This profile is added in the given output JSON file.')
parser.add_argument('inputTIT', type=argparse.FileType('r'), help='The input TIT file')
parser.add_argument('outputJSON', type=str, help='The output JSON workload file in which the profile will be added')
parser.add_argument('profileName', type=str, help='The name of the profile to generate')
parser.add_argument('jobCommand', type=str, help='The command used to run the job')
parser.add_argument('jobSize', type=int, help='The number of processors used to run the job')
parser.add_argument('jobRuntime', type=float, help='The runtime of the job')
parser.add_argument('-i', '--indent', type=int, default=None, help='If set to a non-negative integer, then JSON array elements and object members will be pretty-printed with that indent level. An indent level of 0, or negative, will only insert newlines. The default value (None) selects the most compact representation.')

args = parser.parse_args()

# Let the TIT file be parsed once to know the number of nodes
input_lines = args.inputTIT.readlines()

ranks = set()

for line in input_lines:
    parts = line.split(' ')
    ranks.add(int(parts[0]))

size = len(ranks)
if size != args.jobSize:
    print("Warning: the MPI size of the trace ({}) does not match the given one ({})".format(size, args.jobSize))
    size = args.jobSize
computation = [0] * size
communication = [[0] * size] * size

# Let the TIT file be traversed again to fill the computation and communication data
for line in input_lines:
    line = line.strip()
    parts = line.split(' ')
    rank = int(parts[0])

    if parts[1] == 'compute':
        comp_amount = float(parts[2])
        computation[rank] = computation[rank] + comp_amount
    elif parts[1] == 'send':
        sender = int(parts[0])
        receiver = int(parts[2])
        comm_amount = float(parts[3])
        communication[sender][receiver] = communication[sender][receiver] + comm_amount
    elif parts[1] == 'bcast':
        root = int(parts[3])
        receiver = int(parts[0])
        comm_amount = float(parts[2])
        if receiver != root:
            communication[root][receiver] = communication[root][receiver] + comm_amount
    elif parts[1] == 'alltoall':
        sender = int(parts[0])
        comm_amount = float(parts[2])
        for receiver in range(size):
            if receiver != sender:
                communication[sender][receiver] = communication[sender][receiver] + comm_amount
    elif parts[1] == 'reduce':
        sender = int(parts[0])
        root = int(parts[4])
        comm_amount = float(parts[2]) / size
        comp_amount = float(parts[3])
        computation[sender] = computation[sender] + comp_amount
        if root != sender:
            communication[sender][root] = communication[sender][root] + comm_amount
    elif parts[1] == 'init':
        pass
    elif parts[1] == 'finalize':
        pass
    elif parts[1] == 'barrier':
        pass
    else:
        print("Warning: unhandled command '{}' in line '{}'".format(parts[1], line))

# Let the output file be generated
json_data = dict()
json_data['profiles'] = dict()
if os.path.isfile(args.outputJSON):
    # The previous content is loaded if it exists
    try:
        in_json_file = open(args.outputJSON, 'r')
        json_data = json.load(in_json_file)

        if ('profiles' in json_data):
            assert(args.profileName not in json_data['profiles']), "Cannot append profile '{}' in {}: the profile name is already taken".format(args.profileName, args.outputJSON)
        else:
            json_data['profiles'] = dict()
        in_json_file.close()
    except IOError:
        print("Cannot read file ", args.outputJSON)
        raise

json_profile = dict()
json_profile['type'] = 'msg_par'
json_profile["command"] = args.jobCommand
json_profile["np"] = args.jobSize
json_profile["runtime"] = args.jobRuntime
json_profile["cpu"] = computation
json_profile["com"] = [val for sublist in communication for val in sublist]

json_data['profiles'][args.profileName] = json_profile

try:
    out_file = open(args.outputJSON, 'w')
    json.dump(json_data, out_file, indent=args.indent)
    out_file.close()
except IOError:
    print("Cannot write file ", args.outputJSON)
