import os
import shutil
import sys

if len(sys.argv) < 2:
    print("Usage: python strip_database.py <path/to/oeisdata/repo>")
    exit(0)
    
root = sys.argv[1]

# List of files and directories to remove
items_to_remove = ["files", ".gitattributes", ".lfsconfig", "LICENSE", "README.md", "time.txt"]

# Remove the specified files and directories
for item_name in items_to_remove:
    item_path = os.path.join(root, item_name)
    if os.path.exists(item_path):
        if os.path.isfile(item_path):
            os.remove(item_path)
            print(f"Removed file {item_name}")
        elif os.path.isdir(item_path):
            shutil.rmtree(item_path)
            print(f"Removed directory {item_name}")

# Function to parse and process files
def process_file(file_path):
    with open(file_path, 'r', encoding='utf-8', errors='replace') as file:
        lines = file.readlines()

    relevant_lines = []
    contains_formula = False
    for line in lines:
        if '%F' in line:
            contains_formula = True
        if line.startswith(('%I', '%S', '%T', '%N', '%U', '%F', '%p', '%t', '%o')):
            relevant_lines.append(line)

    # Save relevant lines to a new file
    if contains_formula:
        with open(file_path, 'w', encoding='utf-8') as new_file:
            new_file.writelines(relevant_lines)
        return True
    return False

root = os.path.join(root, 'seq')
# Traverse through directories
for dir_name in os.listdir(root):
    dir_path = os.path.join(root, dir_name)
    if os.path.isdir(dir_path):
        # Move all files from the subdirectory to the parent directory
        for file_name in os.listdir(dir_path):
            file_path = os.path.join(dir_path, file_name)
            if os.path.isfile(file_path):
                if process_file(file_path):
                    shutil.move(file_path, root)
        shutil.rmtree(dir_path)
