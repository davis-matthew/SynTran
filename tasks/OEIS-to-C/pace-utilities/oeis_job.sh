#!/bin/bash
#SBATCH --job-name=OEIS          # Job name
#SBATCH --partition=gpu-v100
#SBATCH --output=output_%j.txt     # Output file (%j = job ID)
#SBATCH --gres=gpu:v100:1
#SBATCH --nodelist=atl1-1-01-003-35-0,atl1-1-01-003-36-0,atl1-1-02-006-31-0,atl1-1-02-006-32-0,atl1-1-02-006-33-0,atl1-1-02-006-34-0,atl1-1-02-006-35-0,atl1-1-02-006-36-0,atl1-1-02-007-31-0,atl1-1-02-007-32-0,atl1-1-02-007-33-0,atl1-1-02-007-34-0,atl1-1-02-007-35-0,atl1-1-02-007-36-0,atl1-1-02-008-31-0,atl1-1-02-008-32-0,atl1-1-02-008-33-0,atl1-1-02-008-34-0,atl1-1-02-008-35-0,atl1-1-02-011-35-0
#SBATCH --ntasks=1                 # Number of tasks
#SBATCH --nodes=1
#SBATCH --cpus-per-task=1          # CPUs per task
#SBATCH --time=12:00:00            # Time limit (HH:MM:SS)
#SBATCH --mem=16G                   # Total memory
#SBATCH --account=gts-vganesh45-paid

module load ollama

echo "OEIS Sequence Batch $1"

python3 /storage/home/hcoda1/7/mdavis438/GANESH-SHARED/SynTran/src/syntran.py --task /storage/home/hcoda1/7/mdavis438/GANESH-SHARED/SynTran/tasks/OEIS-to-C/description.json --config /storage/home/hcoda1/7/mdavis438/GANESH-SHARED/SynTran/tasks/OEIS-to-C/pace-utilities/oeis-phoenix-$1.json --recalculate-results none