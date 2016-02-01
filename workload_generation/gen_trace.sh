#!/bin/bash

_script="$(dirname $(readlink -f ${BASH_SOURCE[0]}))"

EXTRAE_HOME=/opt/extrae
NPB_BIN=/root/NPB3.3.1/NPB3.3-MPI/bin/

NBPROC=$(uniq $OAR_NODEFILE | wc -l)
CMDS=$(ls -1 $NPB_BIN | grep -E "*\.$NBPROC$")
RESULTS=/root/results/

mkdir -p $RESULTS
cd $RESULTS

export LD_PRELOAD=$EXTRAE_HOME/lib/libmpitrace.so
export export EXTRAE_CONFIG_FILE=$_script/extrae.xml
for cmd in $CMDS
do
  mpirun -np $NBPROC --mca orte_rsh_agent "oarsh" -machinefile $OAR_NODEFILE $NPB_BIN/$cmd
  $_script/prv2tit.pl -i $cmd > $cmd.tit
done
