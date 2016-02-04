#!/bin/bash

_script="$(dirname $(readlink -f ${BASH_SOURCE[0]}))"

EXTRAE_TRACE_DIR=/home/mmercier/results/exp2016-02-02
TIT_TRACE_DIR=/home/mmercier/results/exp2016-02-02/tit
CMDS=$(ls -1 $EXTRAE_TRACE_DIR | grep prv | xargs -I{} basename {} .prv)

mkdir -p $TIT_TRACE_DIR

i=0;
waitevery=$(nproc);
for cmd in $CMDS
do
  $_script/prv2tit.pl -i $EXTRAE_TRACE_DIR/$cmd > $TIT_TRACE_DIR/$cmd.tit & (( i++%waitevery==0 )) && wait
done
wait
