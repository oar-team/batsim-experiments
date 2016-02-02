#!/bin/bash

_script="$(dirname $(readlink -f ${BASH_SOURCE[0]}))"

EXTRAE_TRACE_DIR=$_script/tests/prv
TIT_TRACE_DIR=$_script/tests/tit
CMDS=$(ls -1 $EXTRAE_TRACE_DIR | xargs -I{} basename {} .prv)

mkdir -p $TIT_TRACE_DIR

i=0;
waitevery=4;
for cmd in $CMDS
do
  $_script/prv2tit.pl -i $EXTRAE_TRACE_DIR/$cmd > $TIT_TRACE_DIR/$cmd.tit & (( i++%waitevery==0 )) && wait
done
wait
