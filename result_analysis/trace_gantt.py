#!/usr/bin/python3
'''
This script provides a gantt chart view of an output CSV job file from
Batsim using *evalys* module.
'''

import argparse
import os
import matplotlib.pyplot as plt
from evalys.jobset import JobSet


def main():
    parser = argparse.ArgumentParser(description='Generate Gantt charts '
                                     'from Batsim CSV job file.')
    parser.add_argument('inputCSV', nargs='+', help='The input CSV file(s)')

    args = parser.parse_args()

    fig, ax_list = plt.subplots(len(args.inputCSV), sharex=True,
                                sharey=True)
    if not isinstance(ax_list, list):
        ax_list = list(ax_list)

    for ax, inputCSV in zip(ax_list, sorted(args.inputCSV)):
        js = JobSet(inputCSV)
        js.gantt(ax, os.path.basename(inputCSV))

    plt.show()

    # print(js.df.describe())

    # js.df.hist()


if __name__ == "__main__":
    main()
