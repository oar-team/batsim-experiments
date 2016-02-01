#!/bin/bash

_script="$(dirname $(readlink -f ${BASH_SOURCE[0]}))"

EXTRAE_HOME=/opt/extrae
NPB_BIN=/root/NPB3.3.1/NPB3.3-MPI/bin/

OAR_NODEFILE=$_script/hostfile
NBPROC=$(uniq $OAR_NODEFILE | wc -l)
CMDS=$(ls -1 $NPB_BIN | grep -E "*\.$NBPROC$")
RESULTS=/root/results/

mkdir -p $RESULTS
cd $RESULTS

export LD_PRELOAD=$EXTRAE_HOME/lib/libmpitrace.so
export EXTRAE_CONFIG_FILE=$_script/extrae.xml

for cmd in $CMDS
do
  echo "Running command $cmd"
  mpirun -machinefile $OAR_NODEFILE -x LD_PRELOAD -x EXTRAE_CONFIG_FILE $NPB_BIN/$cmd
  $_script/prv2tit.pl -i $cmd > $cmd.tit
done
