#!/bin/bash

_script="$(dirname $(readlink -f ${BASH_SOURCE[0]}))"

EXTRAE_HOME=/opt/extrae
NPB_BIN=$_script/NPB3_bin/

NBPROC=$(uniq $OAR_NODEFILE | wc -l)
CMDS=$(ls -1 $NPB_BIN | grep -E "*\.$NBPROC$")
RESULTS=$HOME/results/exp$(--iso-8601="minutes")

mkdir -p $RESULTS
cd $RESULTS

for cmd in $CMDS
do
  echo "Running command $cmd"
  mpirun -machinefile $OAR_NODEFILE -x LD_PRELOAD=$EXTRAE_HOME/lib/libmpitrace.so -x EXTRAE_CONFIG_FILE=$_script/extrae.xml $NPB_BIN/$cmd
done
