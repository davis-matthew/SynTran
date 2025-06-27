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
    args = args.parse_args()

    return args

def load_config(config_path):
    with open(config_path, 'r') as file:
        config = json.load(file)
    return config

def create_clients(config):
    return [None] * config['gpus']

def load_task(task_path):
    #TODO: replace all?
    with open(task_path, 'r') as file:
        task = json.load(file)
    task['prompts']['system'] = task['prompts']['system'].replace('+SPEC_INPUT+', task['specifications']['input']).replace('+SPEC_OUTPUT+', task['specifications']['output'])
    return task

def load_code(config):
    code_paths = config['code']
    code = []
    for code_path in code_paths:
        with open(code_path, 'r') as file:
            code.append(file.read())
    return code

def load_components(module_name, file_name):
    spec = importlib.util.spec_from_file_location(module_name, {file_name})
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    print(f"Loaded {module_name} from {file_name}")

def init_preprocessor():
    load_components('preprocessor','preprocess.py')
def init_verifier():
    load_components('verifier','verify.py')

def init_ollama(config):
    subprocess.run(['./start_ollama.sh', config], cwd=os.path.dirname(os.path.abspath(__file__)))
    print("Ollama Initialized")

def load_model_on_gpu(clients, gpu, llm):
    base_port = config.get('base_port', 11434)
    while True:
        try:
            print(f"initializing model {llm} on {base_port+gpu}")
            clients[gpu] = ollama.Client(host="http://localhost:"+str(base_port+gpu), timeout = config['connection_timeout'])
            response = clients[gpu].chat(
                model=llm, 
                messages=[{"role": "system", "content": "Initializing model"}]
            )
            if response:
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

def preload_model(llm):
    with concurrent.futures.ThreadPoolExecutor(max_workers=config['gpus']) as executor:
        futures = [executor.submit(load_model_on_gpu, gpu, llm) for gpu in range(config['gpus'])]
        concurrent.futures.wait(futures)
    print("Model loaded on GPUs")