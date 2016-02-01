#!/bin/bash

_script="$(dirname $(readlink -f ${BASH_SOURCE[0]}))"

EXTRAE_TRACE_DIR=tests/prv
TIT_TRACE_DIR=tests/tit
NPB_BIN=$_script/NPB3_bin/
CMDS=$(ls -1 $EXTRAE_TRACE_DIR | grep .prv)

mkdir -p $TIT_TRACE_DIR

i=0;
waitevery=4;
for cmd in $CMDS
do
  $_script/prv2tit.pl -i $EXTRAE_TRACE_DIR/$cmd > $TIT_TRACE_DIR/$cmd.tit & (( i++%waitevery==0 )) && wait
done
