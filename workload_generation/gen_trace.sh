#!/bin/bash

kadeploy3 -f $OAR_NODEFILE -a ~/my_g5k_images/debian8_workload_generation.dsc -k

_script="$(dirname $(readlink -f ${BASH_SOURCE[0]}))"

EXTRAE_HOME=/opt/extrae
NPB_BIN=$_script/NPB_bin/

NBPROC=$(uniq $OAR_NODEFILE | wc -l)
CMDS=$(ls -1 $NPB_BIN | grep -E "*\.$NBPROC$")
RESULTS=$HOME/results/exp$(date --iso-8601)

mkdir -p $RESULTS
cd $RESULTS

for cmd in $CMDS
do
  echo "Running command $cmd"
  mpirun --mca btl_tcp_if_exclude ib0,lo,myri0 --mca btl self,sm,tcp -machinefile $OAR_NODEFILE -x LD_PRELOAD=$EXTRAE_HOME/lib/libmpitrace.so -x EXTRAE_CONFIG_FILE=$_script/extrae.xml $NPB_BIN/$cmd
done
