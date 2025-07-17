#!/bin/bash

# Download and prune OEIS entries
git clone --depth 1 https://github.com/oeis/oeisdata.git "$1" # takes a while
python3 "${script_dir}/strip_database.py" "$1" # takes a little less, but still a while