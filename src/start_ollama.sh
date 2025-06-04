#!/bin/bash

CONFIG=$1

# Read the number of GPUs from the config file
NUM_GPUS=$(jq '.gpus' $CONFIG)

PORT=11434

for ((i=0; i<NUM_GPUS; i++)); do
    CUDA_VISIBLE_DEVICES=$i ollama serve --port $(($PORT + i)) &
done

wait