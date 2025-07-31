import os
import shutil
from concurrent.futures import ThreadPoolExecutor, as_completed
from tqdm import tqdm
import sys

def process_file(file_path):
    with open(file_path, 'r', encoding='utf-8', errors='replace') as file:
        lines = file.readlines()

    relevant_lines = []
    seq_values = []
    contains_formula = False
    
    for line in lines:
        if '%F' in line:
            contains_formula = True
        if line.startswith(('%I', '%S', '%T', '%N', '%U', '%F', '%p', '%t', '%o')):
            relevant_lines.append(line)
        if line.startswith(('%S', '%T', '%U')):
            seq_values.extend([int(x) for x in line.split()[2].rstrip(',').split(',')])
    
        
    num_distinct_values = len(set(seq_values))

    # Save relevant lines to a new file
    if not contains_formula or num_distinct_values < 10:
        os.remove(file_path)
    return True

if len(sys.argv) < 2:
    print("Usage: python strip_database.py <path/to/oeisdata/repo>")
    exit(0)
    
root = sys.argv[1]

# Delete all spurious files
for item_name in ["files", ".gitattributes", ".lfsconfig", "LICENSE", "README.md", "time.txt"]:
    item_path = os.path.join(root, item_name)
    if os.path.exists(item_path):
        if os.path.isfile(item_path):
            os.remove(item_path)
            print(f"Removed file {item_name}")
        elif os.path.isdir(item_path):
            shutil.rmtree(item_path)
            print(f"Removed directory {item_name}")

seq_root = os.path.join(root, 'seq')

# Move all files from the subdirectory to the parent directory
for dir_name in os.listdir(seq_root):
    dir_path = os.path.join(seq_root, dir_name)
    if os.path.isdir(dir_path):
        for file_name in os.listdir(dir_path):
            file_path = os.path.join(dir_path, file_name)
            if os.path.isfile(file_path):
                target_path = os.path.join(root, file_name)
                shutil.move(file_path, target_path)

file_paths = [
    entry.path for entry in os.scandir(root)
    if entry.is_file()
]

original_length = len(file_paths)

with ThreadPoolExecutor() as executor:
    futures = {executor.submit(process_file, fp): fp for fp in file_paths}
    for _ in tqdm(as_completed(futures), total=len(futures), desc="Processing files"):
        pass  # progress is updated for each completed file

file_paths = [
    entry.path for entry in os.scandir(root)
    if entry.is_file()
]
reduced_length = len(file_paths)
print(f"Stripped database from {original_length} -> {reduced_length} entries")