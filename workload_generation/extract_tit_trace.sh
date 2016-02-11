#!/bin/bash

_script="$(dirname $(readlink -f ${BASH_SOURCE[0]}))"

EXTRAE_TRACE_DIR=/home/mmercier/expe-batsim/workload_generation/results_2016-02-08--10-10-44
TIT_TRACE_DIR=/home/mmercier/expe-batsim/workload_generation/results_2016-02-08--10-10-44/tit
CMDS=$(ls -1 $EXTRAE_TRACE_DIR | grep prv | xargs -I{} basename {} .prv)
TO_RUN=/tmp/to_run

rm $TO_RUN
mkdir -p $TIT_TRACE_DIR

for cmd in $CMDS
do
  # Do not erase already computed tit files
  if [ ! -f $TIT_TRACE_DIR/$cmd.tit ] || [ ! -s $TIT_TRACE_DIR/$cmd.tit ]
  then
    echo "$_script/prv2tit.pl -i $EXTRAE_TRACE_DIR/$cmd > $TIT_TRACE_DIR/$cmd.tit" >> $TO_RUN
  fi
done

cat $TO_RUN | parallel
