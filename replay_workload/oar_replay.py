#!/usr/bin/env python3
'''
This script is taking a Batsim profile as input and replay the profile
using the provided commands.
'''
import argparse
import os
import json
import sched
import time
import re
import csv
from subprocess import call, Popen, PIPE
from datetime import datetime, timedelta

command_path = "/home/mmercier/expe-batsim/workload_generation/NPB_bin/"


def do_oar_submission(command, walltime, resources, result_dir,
                      batsim_job_id):
    hms_time = timedelta(seconds=walltime)
    oar_time = str(hms_time).split('.')[0]
    exports = 'export PATH=$PATH:{}; '.format(command_path)
    oar_options = '--stdout={0}/OAR%jobid%.stdout --stderr={0}/OAR%jobid%.stderr '.format(workload_dir)
    oar_cmd = (exports + '/usr/bin/oarsub ' + oar_options + ' -l \\nodes=' + str(resources) + ',walltime=' +
               oar_time + ' "' + command + '"')
    print(oar_cmd)
    with Popen(oar_cmd, stdout=PIPE, shell=True) as oar_cmd:
        stdout = oar_cmd.stdout.read().decode()
        find_job = re.search("\\nOAR_JOB_ID=(.*)\\n", stdout)
        if find_job:
            job_id = int(find_job.group(1))
            writer.writerow({"batsim_id": batsim_job_id, "oar_id": job_id})
        else:
            print("JOB_NOT_SUBMITTED_BATSIM_JOB_ID: {}".format(batsim_job_id))


def get_scheduling_results(results_file):
    fmt = '%Y-%m-%d %X'
    oar_gantt_cmd = ('oarstat -J --gantt "' + begin.strftime(fmt) + ',' +
                     end.strftime(fmt) + '" > ' + str(results_file))
    print(oar_gantt_cmd)
    call(oar_gantt_cmd, shell=True)

    with open(results_file, "r") as res_file:
        json_data = json.load(res_file)
    jobs = json_data['jobs']
    jobs_details = {}

    for job_id in jobs:
        with Popen(['oarstat', '-Jfj', job_id], stdout=PIPE) as oarstat:
            jobs_details[job_id] = json.loads(oarstat.stdout.read().decode())[job_id]

    with open(results_file + '.details', "w") as job_file:
        json.dump({"jobs": jobs_details }, job_file, sort_keys=True, indent=4)


parser = argparse.ArgumentParser(description='Replay Batsim profile using'
                                             'OAR submitions')
parser.add_argument('inputJSON',
                    type=argparse.FileType('r'),
                    help='The input JSON Batsim profiles file')
parser.add_argument('result_dir',
                    help='The result directory to put the result and find the hostname')
parser.add_argument('outputJSON',
                    help='The output JSON OAR gantt file. It will be put in the result_dir')

args = parser.parse_args()

# parse the workload to get jobs
json_data = json.load(args.inputJSON)
assert('profiles' in json_data), ("Invalid input file: It must contains a"
                                  "'profiles' map")

# get informations
workload = os.path.splitext(os.path.basename(args.inputJSON.name))[0]
jobs = json_data['jobs']
profiles = json_data['profiles']
result_dir = args.result_dir


# schedule the jobs
begin = datetime.now()

scheduler = sched.scheduler(time.time, time.sleep)
for job in jobs:
    # get command
    cmd = profiles[job['profile']]['command']
    job_id = job['id']
    scheduler.enter(job['subtime'],
                    0,
                    do_oar_submission,
                    kwargs={'command': cmd,
                            'walltime': job['walltime'],
                            'resources': job['res'],
                            'result_dir': args.result_dir,
                            'batsim_job_id': job_id})

# prepare output directory
workload_dir = result_dir + '/' + workload
try:
    os.mkdir(workload_dir)
except OSError as exc:
    if exc.errno != os.errno.EEXIST:
        raise exc

# prepare output file
try:
    csv_file = open(result_dir + '/' + workload + '-job_id_mapping.csv', 'w', newline='')
    writer = csv.DictWriter(csv_file, fieldnames=["batsim_id", "oar_id"])
    writer.writeheader()

    # run the jobs
    scheduler.run()
finally:
    csv_file.close()

while True:
    process = call("oarstat > /tmp/out" , shell=True)
    if os.stat("/tmp/out").st_size == 0:
        break
    time.sleep(1)

end = datetime.now()

get_scheduling_results(args.result_dir + '/' + args.outputJSON)
