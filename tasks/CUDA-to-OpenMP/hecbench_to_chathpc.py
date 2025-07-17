import re
import os
import json

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

def code_similarity(code1: str, code2: str) -> float:    
    vectorizer = TfidfVectorizer()
    tfidf_matrix = vectorizer.fit_transform([code1, code2])
    return cosine_similarity(tfidf_matrix[0], tfidf_matrix[1])[0][0]

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

    if not ((os.path.exists(cuda_dir) and os.path.isdir(cuda_dir)) and (os.path.exists(omp_dir) and os.path.isdir(omp_dir))):
        print("problem does not have both omp and cuda implementations")
        exit(0)
    kernel_map = {}

    # Extract CUDA kernels
    for file in os.listdir(cuda_dir):
        if file.endswith(".cu") or file.endswith(".h"):
            filepath = os.path.join(cuda_dir, file)
            kernels = extract_functions(filepath, cuda_pattern)
            for name, kernel in kernels:
                kernel_map[name] = kernel

    matched_pairs = []

    # Extract OpenMP functions and match name w/ CUDA kernels
    need_to_match = set(list(kernel_map.keys()))
    for file in os.listdir(omp_dir):
        if file.endswith(".cpp") or file.endswith(".h"):
            filepath = os.path.join(omp_dir, file)
            functions = extract_functions(filepath, cpp_pattern)
            for name, kernel in functions:
                if name in kernel_map:
                    matched_pairs.append((name, kernel_map[name], kernel))
                    need_to_match.remove(name)
    
    need_to_match = list(need_to_match)
    # Find candidate matchings as needed for cuda kernels:
    while len(need_to_match) > 0:
        similarities = []
        for name, kernel in functions:
            similarities.append((name.strip().replace("\n",""), code_similarity(kernel_map[need_to_match[0]], kernel)))
        similarities = sorted(similarities, key=lambda x: x[1])

        print(similarities)
        while True:
            print(f'Matching Kernel {need_to_match[0]}:')
            print('\tOpenMP Function Name:\tCosine Similarity:')
            i = 0
            for similarity in similarities:
                print(f'{i}.\t{similarity[0]}\t{similarity[1]}')
                i+=1
            match = input(f"\n\nWhich option would you like to match? (0-{len(similarities)-1}): ")
            try:
                if int(match) >= 0 and int(match) < len(similarities):
                    matched_pairs.append((name, kernel_map[need_to_match[0]], kernel))
                    need_to_match.pop(0)
                else:
                    print("Out of range")
            except:
                print("Invalid choice")

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