#!/bin/env bash
# Copyright (C) 2007  The Trustees of Indiana University
#
# Use, modification and distribution is subject to the Boost Software
# License, Version 1.0. (See accompanying file LICENSE_1_0.txt or copy at
# http://www.boost.org/LICENSE_1_0.txt)
#
# Authors: Douglas Gregor
#          Andrew Lumsdaine
#
# Shell script used to help execute MPI.NET tests for a varying number
# of processes.
#
# Usage:
#   cd path/to/MPI.NET
#   ./Tests/runtest.sh ./Tests/BroadcastTest "4"
MPIEXEC=mpiexec

# The test we will be executing
test_name=$1

# force the test schedule
force_proc_schedule=$2

# Find the absolute path from the relative BUILDDIR we are given
#OLDDIR=`pwd`
#cd $BUILDDIR
#BUILDDIR=`pwd`
#cd $OLDDIR

# Set up the path for the dynanamic linker
#if test `uname` == "Darwin" ; then
#  export DYLD_LIBRARY_PATH=$BUILDDIR/MPI/.libs:$DYLD_LIBRARY_PATH
#else
#  export LD_LIBRARY_PATH=$BUILDDIR/MPI/.libs:$LD_LIBRARY_PATH
#fi

# Compute the testing schedule, i.e., the numbers of processors for
# which we will execute the program.
test_schedule="1 2 7 8 13 16 21"
case "$test_name" in
  *Ring ) test_schedule="2 7 8 13 16 21" ;;
  *Netpipe ) test_schedule="2" ;;
  *Netcoll ) test_schedule="8" ;;
  *CartTest ) test_schedule="8" ;;
  *GraphTest ) test_schedule="4 7 8 13 16 21" ;;
  *DatatypesTest ) test_schedule="2" ;;
  *ExceptionTest ) test_schedule="2" ;;
  *IntercommunicatorTest ) test_schedule="2 7 8 13 16 21" ;;
esac

if test "$force_proc_schedule" != "" ; then
  test_schedule="$force_proc_schedule"
fi

result_code=0

echo "INFO: test_name=$test_name"
echo "INFO: LD_LIBRARY_PATH=$LD_LIBRARY_PATH"

for procs in $test_schedule ; do
  echo $MPIEXEC -n $procs $test_name/bin/Debug/net6.0/$test_name
  $MPIEXEC -n $procs $test_name/bin/Debug/net6.0/$test_name
  if test $? == 0 ; then
    echo "PASS $test_name (with $procs processes)"
  else
    echo "FAIL $test_name (with $procs processes)"
    result_code=-1
  fi
done

exit $result_code
