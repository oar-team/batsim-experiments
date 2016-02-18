#!/usr/bin/python3
'''
This script provides a gantt chart view of an output CSV job file from
Batsim using *evalys* module.
'''

import argparse
import csv
from evalys.jobset import JobSet

parser = argparse.ArgumentParser(description='Generate Gantt charts from Batsim CSV job file.')
parser.add_argument('inputCSV', help='The input CSV file')

args = parser.parse_args()

js = JobSet(args.inputCSV)
print(js.df.describe())

js.df.hist()
js.gantt()
