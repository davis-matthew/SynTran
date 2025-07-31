import os
from concurrent.futures import ThreadPoolExecutor, as_completed
from tqdm import tqdm

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

dir_path = '/storage/home/hcoda1/7/mdavis438/GANESH-SHARED/SynTran/tasks/OEIS-to-C/external/oeisdata/seq'
file_paths = [
    entry.path for entry in os.scandir(dir_path)
    if entry.is_file()
]

with ThreadPoolExecutor() as executor:
    futures = {executor.submit(process_file, fp): fp for fp in file_paths}
    for _ in tqdm(as_completed(futures), total=len(futures), desc="Processing files"):
        pass  # progress is updated for each completed file
