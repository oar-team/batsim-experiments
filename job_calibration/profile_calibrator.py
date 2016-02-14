#!/usr/bin/python3

'''
This script reads a Batsim JSON profiles file and modifies its profiles
according to another input file which says how the communication vector and
communication matrix should be modified.

The input file is read line by line and its modifications are done online.
Hence, several modifications can be applied on the same profile without
needing to run this script multiple times. An example of such file is
below:

Syntax: PROFILE_NAME command [command-dependent parameters]
        PROFILE_NAME scale COMPUTATION_SCALE COMMUNICATION_SCALE
'
ft.C.32 scale 1 0.5
lu.D.4 scale 2 1.25
'

'''

import argparse
import math
import sys
import random
import pandas
import json
import os
import datetime

parser = argparse.ArgumentParser(description='Modifies the profiles of a Batsim JSON profiles file according to another input file which says how the communication vector and communication matrix should be modified.')
parser.add_argument('inputJSON', type=argparse.FileType('r'), help='The input JSON profiles file')
parser.add_argument('inputModifications', type=argparse.FileType('r'), help='The input file which contains the modifications to apply to the profiles')
parser.add_argument('outputJSON', type=argparse.FileType('w'), help='The output JSON profiles file')
parser.add_argument('-i', '--indent', type=int, default=None, help='If set to a non-negative integer, then JSON array elements and object members will be pretty-printed with that indent level. An indent level of 0, or negative, will only insert newlines. The default value (None) selects the most compact representation.')

args = parser.parse_args()

json_data = json.load(args.inputJSON)
assert('profiles' in json_data), "Invalid input file: there must be a 'profiles' map in it"

# Let the TIT file be parsed once to know the number of nodes
input_lines = args.inputModifications.readlines()

for line in input_lines:
    line = line.strip()

    if line == '':
        continue

    parts = line.split(' ')

    if len(parts) < 2:
        print("Warning: line '{}' of file '{}' has been skipped: it does not contain at least 2 space-separated parts".format(line, args.inputJSON.name))
        continue

    profile = parts[0]
    command = parts[1]

    if profile not in json_data['profiles']:
        print("Warning: line '{}' of file '{}' has been skipped: the profile '{}' does not exist".format(line, args.inputJSON.name, profile))
        continue

    if command == 'scale':
        if len(parts) != 4:
            print("Warning: line '{}' of file '{}' has been skipped: invalid scale command: it must be composed of 4 space-separated parts".format(line, args.inputJSON.name))
            continue
        comp_scale = float(parts[2])
        comm_scale = float(parts[3])

        comp_vector = json_data['profiles'][profile]['cpu']
        comm_matrix = json_data['profiles'][profile]['com']

        # Update computation vector
        json_data['profiles'][profile]['cpu'] = [float(x) * comp_scale for x in comp_vector]
        # Update communication matrix
        json_data['profiles'][profile]['com'] = [float(x) * comm_scale for x in comm_matrix]
    else:
        print("Warning: line '{}' of file '{}' has been skipped: command '{}' is unknown".format(line, args.inputJSON.name, command))

try:
    json.dump(json_data, args.outputJSON, indent=args.indent)
    args.outputJSON.close()
except IOError:
    print("Cannot write file ", args.outputJSON)
