import argparse

# This script is responsible for setting up the Invariant-Generation task components
args = argparse.ArgumentParser(description="command-line flag parser")
args.add_argument("", help="Options:\n\tbase : sets up required components for SynTran\n\tcompare : sets up required components for SynTran & builds tools used in comparison")
args = args.parse_args()

####
run setup_wp.sh

run autospec.sh
run esbmc-ibmc.sh
run lemur.sh
run loopy.sh
