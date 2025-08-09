#!/bin/bash
SCRIPT_DIR="$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
cd "${SCRIPT_DIR}"

# Download and prune OEIS entries
git clone --depth 1 https://github.com/oeis/oeisdata.git "$1" # takes a while
python3 "${SCRIPT_DIR}/strip_database.py" "$1" # takes a little less, but still a while