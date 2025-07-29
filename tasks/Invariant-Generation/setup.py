import subprocess
import os

setup_evaluation = input("Set up evaluation comparisons (Y/N)?: ")

script_dir = os.path.dirname(os.path.abspath(__file__))

# Frama-C and WP
subprocess.run([os.path.join(script_dir, "setup_wp.sh")], shell=True)

# Pluto
subprocess.run([os.path.join(script_dir, "setup_pluto.sh")], shell=True)

# Setup Evaluations
if setup_evaluation == 'Y':
    subprocess.run([os.path.join(script_dir, "setup_comparisons.sh")], shell=True)