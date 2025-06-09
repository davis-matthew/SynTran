# SynTran Quickstart Guide

To use the tool follow these steps:

1. Create a config. You can see example configs in `configs/`. This sets up the resources and problem timeout and such for a given computer.
2. Create a task description. Again, there are example tasks in `tasks/`, which have a `description.json` file. Note that this will probably require some extra scripts to handle preprocessing and verification, also potentially installation of external tools like solvers.
3. Run syntran.py ```python3 src/syntran.py --config="path/to/config.json" --task="path/to/task/description.json" path/to/code/file```