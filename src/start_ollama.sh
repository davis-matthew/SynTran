#!/bin/bash
module load ollama
CONFIG=$1

# Read the number of GPUs from the config file
NUM_GPUS=$(grep '"gpus"' "$CONFIG" | awk -F ': ' '{print $2}' | tr -d ',')

# Starting port number for ollama instances
BASE_PORT=$(grep '"base_port"' "$CONFIG" | awk -F ': ' '{print $2}' | tr -d ',')
BASE_PORT=${BASE_PORT:-11434}

for ((i=0; i<NUM_GPUS; i++)); do
    PORT=$(($BASE_PORT + i))
    CUDA_VISIBLE_DEVICES=$i OLLAMA_HOST="127.0.0.1:${PORT}" OLLAMA_KEEP_ALIVE="16h" OLLAMA_LOAD_TIMEOUT="30m" nohup ollama serve & #> ollama_logs/11434.txt 2>&1 & # FIXME: change log path

    (
        while ! nc -z 127.0.0.1 $PORT; do
            sleep 1
        done
        echo "Ollama started on port $PORT"
    ) &

    OLLAMA_STARTUP_PROCESSES+=($!)
done

wait "${OLLAMA_STARTUP_PROCESSES[@]}"
