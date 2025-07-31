#!/bin/bash

# Check if a folder was provided
if [ -z "$1" ]; then
  echo "Usage: $0 <root-folder>"
  exit 1
fi

ROOT_DIR="$1"

# Find all subdirectories ending with -omp
find "$ROOT_DIR" -type d -name '*-omp' | while read -r dir; do
  MAKEFILE="$dir/Makefile"
  if [ -f "$MAKEFILE" ]; then
    echo "Processing $MAKEFILE"
    sed -i \
      -e 's/\bicpc\b/g++/g' \
      -e 's/\bicpx\b/g++/g' \
      -e 's/-fopenmp-targets=[^[:space:]]*//g' \
      -e 's/-qnextgen//g' \
      -e 's/-fiopenmp/-fopenmp/g' \
      "$MAKEFILE"
  else
    echo "No Makefile found in $dir"
  fi
done