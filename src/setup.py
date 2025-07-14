import argparse
import json
import importlib
import sys
import time
import concurrent
import ollama
import os
import subprocess

def parse_args():
    args = argparse.ArgumentParser(description="command-line flag parser")
    args.add_argument("--config", type=str, required=True, help="Path to config .json file")
    args.add_argument("--task", type=str, required=True, help="Path to task description .json file")
    args.add_argument("--recalculate-results", type=str, default=None, help="all (solutions and terminated recalculated), terminated (keep solutions, but retry terminated), none (keep both solution and terminated, run on any new files)")
    args = args.parse_args()

    return args

def load_config(config_path):
    with open(config_path, 'r') as file:
        config = json.load(file)
    return config

def create_chat_clients(config):
    return [None] * config['gpus']

def load_task(task_path):
    with open(task_path, 'r') as file:
        task = json.load(file)
    
    for key in task['prompts']:
        task['prompts'][key] = (
            task['prompts'][key]
            .replace('+SPEC_INPUT+', task['specifications']['input'])
            .replace('+SPEC_OUTPUT+', task['specifications']['output'])
        )
    return task

def load_code(config):
    code_paths = config['code']
    code = []
    config['code_paths'] = []
    for code_path in code_paths:
        temp = [code_path]
        if os.path.isdir(code_path):
            temp = (os.path.join(code_path,f) for f in os.listdir(code_path) if os.path.isfile(os.path.join(code_path, f)))
        
        for path in temp:
            config['code_paths'].append(path)
            with open(path, 'r') as file:
                code.append(file.read())
    return code

def load_components(module_name, file_name):
    spec = importlib.util.spec_from_file_location(module_name, file_name)
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    print(f"Loaded {module_name} from {file_name}")

def init_preprocessor(task_dir):
    load_components('preprocessor',f'{task_dir}/preprocess.py')
def init_verifier(task_dir):
    load_components('verifier',f'{task_dir}/verify.py')

def init_ollama(config):
    subprocess.run(['./start_ollama.sh', config], cwd=os.path.dirname(os.path.abspath(__file__)))
    print("Ollama Initialized")

def load_model_on_gpu(chat_clients, config, gpu, llm):
    base_port = config.get('base_port', 11434)
    while True:
        try:
            print(f"initializing model {llm} on {base_port+gpu}")
            chat_clients[gpu] = ollama.Client(host="http://localhost:"+str(base_port+gpu), timeout = config['connection_timeout'])
            response = chat_clients[gpu].chat(
                model=llm, 
                messages=[{"role": "system", "content": "Initializing model"}]
            )
            if response:
                print(response.text)
                print(f"SUCCESS - loaded model {llm} on gpu {gpu}")
                return True
            else:
                print(f"ERROR - failed to load model on gpu")
        except Exception as e:
            e = str(e)
            if "Access Denied" in e or "ERR_ACCESS_DENIED" in e:
                print("ERROR - Access Denied. Removing http_proxy and https_proxy and retrying")
                os.environ.pop("http_proxy", None)
                os.environ.pop("https_proxy", None)
            else:
                print(f"ERROR - failed to load model on gpu (could not send request) - {e}")
        time.sleep(0.5) # Prevent tight looping

def preload_model(config, llm):
    result = subprocess.run(
        ["ollama", "list"],
        capture_output=True,
        text=True,
        check=True
    )
    if llm not in result.stdout:
        print(f"Pulling model {llm}")
        subprocess.run(["ollama", "pull", llm], check=True)

    with concurrent.futures.ThreadPoolExecutor(max_workers=config['gpus']) as executor:
        futures = [executor.submit(load_model_on_gpu, config, gpu, llm) for gpu in range(config['gpus'])]
        concurrent.futures.wait(futures)
    print("Model loaded on GPUs")