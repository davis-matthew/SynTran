import os
import shutil
from concurrent.futures import ThreadPoolExecutor, as_completed
from tqdm import tqdm
import sys
import threading
import traceback

class ThreadSafeCounter:
    def __init__(self):
        self._value = 0
        self._lock = threading.Lock()

    def increment(self):
        with self._lock:
            self._value += 1

    def get(self):
        with self._lock:
            return self._value

closedform_filter = ThreadSafeCounter()
keyword_filter = ThreadSafeCounter()
distinct_val_filter = ThreadSafeCounter()

def process_file(file_task):
    global closedform_filter
    global keyword_filter
    global distinct_val_filter

    try:
        src, dst = file_task
        with open(src, 'r', encoding='utf-8', errors='replace') as file:
            lines = file.readlines()

        relevant_lines = []
        seq_values = []
        seq_keywords = []
        contains_formula = False
        
        for line in lines:
            if line.startswith(('%I', '%S', '%T', '%N', '%U', '%F', '%p', '%t', '%o')):
                relevant_lines.append(line)
            if '%F' in line:
                contains_formula = True
            if line.startswith(('%S', '%T', '%U')):
                seq_values.extend([int(x) for x in line.split()[2].rstrip(',').split(',')])
            if line.startswith('%K'):
                seq_keywords.extend([x for x in line.split()[2].rstrip(',').split(',')])
            
        num_distinct_values = len(set(seq_values))
        seq_keywords = set(seq_keywords)

        os.remove(src)
        
        if not contains_formula:
            closedform_filter.increment()
            return
        if not len({'bref', 'dead', 'dumb', 'word', 'hard'}.intersection(seq_keywords)) == 0:
            keyword_filter.increment()
            return
        if not num_distinct_values >= 10:
            distinct_val_filter.increment()
            return
        
        # Save relevant lines to a new file
        with open(dst, 'w', encoding='utf-8') as file:
            file.writelines(relevant_lines)
    except Exception as e:
        print(f'error in: {src}')
        traceback.print_exc()

def collect_files(root):
    result = []

    def scan_dir(current_path):
        with os.scandir(current_path) as entries:
            for entry in entries:
                if entry.is_file():
                    full_path = entry.path
                    relative_path = os.path.join(root, entry.name)
                    result.append((full_path, relative_path))
                elif entry.is_dir(follow_symlinks=False):
                    scan_dir(entry.path)

    scan_dir(root)
    return result


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

# Move all files from the subdirectory to the parent directory
file_paths = collect_files(root)
original_length = len(file_paths)

with ThreadPoolExecutor() as executor:
    futures = {executor.submit(process_file, task): task for task in file_paths}
    for _ in tqdm(as_completed(futures), total=len(futures), desc="Pruning & Preprocessing Sequences"):
        pass

print("Removing seq folder...")
shutil.rmtree(os.path.join(root, 'seq'))

reduced_length = len(collect_files(root))
print(f"\nStripped database from {original_length} -> {reduced_length} entries")

print(f"No Closed Form Filter: {original_length} -> {original_length - closedform_filter.get()}")
original_length -= closedform_filter.get()

print(f"Keyword Filter: {original_length} -> {original_length - keyword_filter.get()}")
original_length -= keyword_filter.get()

print(f"Distinct Value Filter: {original_length} -> {original_length - distinct_val_filter.get()}")
original_length -= distinct_val_filter.get()