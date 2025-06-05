import re
import os
import json

def extract_functions(filename, pattern):
    # Find function header
    with open(filename, 'r') as f:
        code = f.read()
    code = "\n".join([line.strip() for line in code.split("\n")])
    matches = pattern.finditer(code)
    
    # Find closing brace to read the entire function
    functions = []
    for match in matches:
        header = match.group(0).strip()
        name = match.group(1).strip().split(" ")[-1]
        start_idx = match.end()
        brace_count = 1
        end_idx = start_idx

        while end_idx < len(code) and brace_count > 0:
            if code[end_idx] == '{':
                brace_count += 1
            elif code[end_idx] == '}':
                brace_count -= 1
            end_idx += 1
        
        body = code[start_idx:end_idx]
        functions.append((name, header+body.strip()+'}'))

    return functions

def find_matching_pairs(cuda_dir, omp_dir):
    cuda_pattern = re.compile(r'(__global__\s+\w+\s+(\w+))\s*\([^)]*\)\s*\{')
    cpp_pattern = re.compile(r'((?:template\s*<[^>]+>\s*)?(?:inline\s*)?(?:[\w:*]+(?:\s+[\w:*]+)*)\s+(\w+))\s*\([^)]*\)\s*\{')

    kernel_map = {}

    # Extract CUDA kernels
    for file in os.listdir(cuda_dir):
        if file.endswith(".cu"):
            filepath = os.path.join(cuda_dir, file)
            kernels = extract_functions(filepath, cuda_pattern)
            for name, kernel in kernels:
                kernel_map[name] = kernel

    matched_pairs = []

    # Extract OpenMP functions and match name w/ CUDA kernels
    for file in os.listdir(omp_dir):
        if file.endswith(".cpp"):
            filepath = os.path.join(omp_dir, file)
            functions = extract_functions(filepath, cpp_pattern)
            for name, kernel in functions:
                if name in kernel_map:
                    matched_pairs.append((name, kernel_map[name], kernel))

    #TODO: maybe some sort of similarity metric if the kernels are not named the same?

    return matched_pairs

base_path = input("path to HeCBench/: ")
problem = input("problem name: ")
matches = find_matching_pairs(f'{base_path}/src/{problem}-cuda', f'{base_path}/src/{problem}-omp')

generated = []

for kernel in matches:
    generated.append({
        "question" : f"Can you translate this CUDA code to OpenMP offload kernel?\n{kernel[1]}",
        "context" : "CUDA to OpenMP offload kernel translation",
        "answer" : kernel[2]
    })

with open("kernel.json", "w") as f:
    json.dump(generated, f, indent=2)