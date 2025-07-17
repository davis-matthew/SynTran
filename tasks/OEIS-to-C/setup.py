import subprocess
import os

script_dir = os.path.dirname(os.path.abspath(__file__))
setup_script = os.path.join(script_dir, "setup.sh")

subprocess.run([setup_script, input("OEIS download directory: ")], shell=True)