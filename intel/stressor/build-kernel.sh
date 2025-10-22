#!/bin/bash 

while [ true ]; do
	echo "Starting Kernel build"
	START_TIME=$(date +%s.%N)
	make -j$(nproc)
	END_TIME=$(date +%s.%N)
	DURATION=$(echo "$END_TIME - $START_TIME" | bc)
	echo "Completed building kernel in: $DURATION"
	echo "Cleaning up"
	make clean
done

