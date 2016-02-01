#!/bin/bash

_script="$(dirname $(readlink -f ${BASH_SOURCE[0]}))"

EXTRAE_HOME=/opt/extrae
NPB_BIN=/root/NPB3.3.1/NPB3.3-MPI/bin/

export LD_PRELOAD=$EXTRAE_HOME/lib/libmpitrace.so
export export EXTRAE_CONFIG_FILE=$_script/extrae.xml

NBPROC=2
CMDS=$(ls -1 $NPB_BIN | grep -E "*\.$NBPROC$")

for cmd in $CMDS
do
  mpirun -np $NBPROC --mca orte_rsh_agent "oarsh" -machinefile $OAR_NODEFILE $cmd
  $_script/prv2tit.pl -i $cmd > $cmd.tit
done
