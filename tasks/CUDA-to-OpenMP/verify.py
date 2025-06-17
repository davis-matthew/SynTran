import random
import argparse

a = ["illegalmodification", "compilererror", "translationerror"]

result = random.choice(a)

args = argparse.ArgumentParser(description="command-line flag parser")
args.add_argument("output_path", help="The report file path")
args = args.parse_args()


with open(args.output_path, 'w') as file:
    file.write(result+ "\n\nNo feedback given")