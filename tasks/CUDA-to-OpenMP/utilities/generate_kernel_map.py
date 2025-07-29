import os
import re
from pathlib import Path


hecbench_path = input("path to HeCBench/src: ") # '/home/mzu/external/HeCBench/src'
distilled_kernel_path = input("output path to store HeCBench CUDA kernels: ") # '/home/mzu/external/HeCBench-Kernels'
file_info = {}

def extract_cuda_kernels(file_path):
    pattern = re.compile(r'__global__\s+\w+\s+(?P<name>\w+)\s*\([^)]*\)\s*\{', re.DOTALL)
    # Function header
    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
        code = f.read()
    code = "\n".join([line.strip() for line in code.split("\n")])
    matches = pattern.finditer(code)
    
    # Function body
    functions = []
    for match in matches:
        header = match.group(0).strip()
        name = match.group("name").strip()
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
        functions.append((name, header+body.strip()))

    return functions

def find_openmp_function_indices(file_path, function_name):
    with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
        content = f.read()
    # Regex to match C++ function definition (handles basic decorators too)
    pattern = rf'[\w\s:*&]+?\b{function_name}\s*\([^)]*\)\s*\{{'
    matches = list(re.finditer(pattern, content))
    
    if not matches:
        return None

    start_index = matches[0].start()
    # Find end index by matching closing brace - simplified brace counter
    brace_count = 0
    end_index = start_index
    while end_index < len(content):
        if content[end_index] == '{':
            brace_count += 1
        elif content[end_index] == '}':
            brace_count -= 1
            if brace_count == 0:
                break
        end_index += 1

    return (start_index, end_index + 1)

def distill_cuda_kernels(input_folder, output_folder):
    os.makedirs(output_folder, exist_ok=True)
    for subdir in os.listdir(input_folder):
        subpath = os.path.join(input_folder, subdir)
        if os.path.isdir(subpath) and '-' in subdir:
            problem, _ = subdir.rsplit('-', 1)
            # Both CUDA & OpenMP must exist
            cuda_path = os.path.join(input_folder, f"{problem}-cuda")
            omp_path = os.path.join(input_folder, f"{problem}-omp")
            if os.path.isdir(cuda_path) and os.path.isdir(omp_path):
                for root, _, files in os.walk(cuda_path):
                    for file in files:
                        if file.endswith('.cu'):
                            full_path = os.path.join(root, file)
                            try:
                                for name, source in extract_cuda_kernels(full_path):
                                    output_file = os.path.join(output_folder, f"{problem}+++{name}.cu")
                                    with open(output_file, 'w') as f:
                                        f.write(source)
                                    print(f"Saved kernels for {problem} to {output_file}")
                            except Exception as e:
                                print(f"Error processing {full_path}: {e}")


distill_cuda_kernels(hecbench_path, distilled_kernel_path)

for filename in os.listdir(distilled_kernel_path):
    file_path = os.path.join(distilled_kernel_path, filename)
    if os.path.isfile(file_path):
        name, _ = os.path.splitext(filename)
        problem = name.split("+++")[0]
        kernel = name.split("+++")[1]
        hecbench_problem_path = Path(hecbench_path) / f'{problem}-omp'
        
        if hecbench_problem_path.exists():
            found = False
            for ext in ("*.cpp", "*.h"):
                for cpp_file in hecbench_problem_path.glob(ext):
                    print(f"checking: {cpp_file}")
                    result = find_openmp_function_indices(cpp_file, kernel)
                    if result:
                        file_info[name] = (str(cpp_file), result[0], result[1])
                        found = True
                        break
                if found:
                    break
            if not found:
                file_info[name] = ("", 0, 0)
        else:
            file_info[name] = ("", 0, 0)

print("{")
for key, data in file_info.items():
    print(f"\t'{key}' : {data},")
print("}")