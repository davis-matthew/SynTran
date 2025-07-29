#!/bin/bash

servers=(
  hudson.ftpn.ornl.gov
  milan0.ftpn.ornl.gov
  milan2.ftpn.ornl.gov
  #xavier1.ftpn.ornl.gov
  #xavier2.ftpn.ornl.gov
  #xavier3.ftpn.ornl.gov
  zenith.ftpn.ornl.gov
)

for server in "${servers[@]}"; do
  echo "$server:"
  ssh "$server" '
    num_gpus=$(nvidia-smi -L | wc -l)
    for ((i=0; i<num_gpus; i++)); do
      procs=$(nvidia-smi --query-compute-apps=pid --format=csv,noheader -i $i)

      if [ -z "$procs" ]; then
        echo "GPU $i is available"
      fi
    done
  '
  echo ""
done