#!/bin/bash

# Number of repetitions
REPEAT=5

# Hostfile location
HOSTFILE="hosts"

# Timeout for each test
TIMEOUT="60s"

# Loop over 5 repetitions
for i in $(seq 1 $REPEAT); do
    echo "Running CPU test iteration $i..."
    mpirun -np 4 -hostfile $HOSTFILE stress-ng --cpu 1 --timeout $TIMEOUT --metrics-brief \
        2>&1 | tee "stress_ng_cpu_run_${i}.txt"

    echo "Running VM test iteration $i..."
    mpirun -np 4 -hostfile $HOSTFILE stress-ng --vm 1 --vm-bytes 512M --timeout $TIMEOUT --metrics-brief \
        2>&1 | tee "stress_ng_vm_run_${i}.txt"

    echo "Running HDD test iteration $i..."
    mpirun -np 4 -hostfile $HOSTFILE \
        bash -c "mkdir -p /tmp/stressng && cd /tmp/stressng && stress-ng --hdd 1 --timeout $TIMEOUT --metrics-brief" \
        2>&1 | tee "stress_ng_hdd_run_${i}.txt"
    
    echo "Finished iteration $i"
    echo "------------------------"
done

echo "All tests completed."
