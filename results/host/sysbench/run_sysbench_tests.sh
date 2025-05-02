#!/bin/bash

# Number of iterations
ITERATIONS=5

# Run CPU test 5 times
echo "Running CPU test $ITERATIONS times..."
for i in $(seq 1 $ITERATIONS); do
    echo "CPU Test Run #$i"
    mpirun -np 4 sysbench --test=cpu --cpu-max-prime=20000 run | tee "sysbench_cpu_result_$i.txt"
done

# Run Memory test 5 times
echo "Running Memory test $ITERATIONS times..."
for i in $(seq 1 $ITERATIONS); do
    echo "Memory Test Run #$i"
    mpirun -np 4 sysbench --test=memory --memory-total-size=10G run | tee "sysbench_mem_result_$i.txt"
done

echo "All tests completed."
