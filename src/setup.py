import argparse
import json
import importlib
import sys
import time
import concurrent
import ollama
import os
import subprocess
import httpx

def parse_args():
    args = argparse.ArgumentParser(description="command-line flag parser")
    args.add_argument("--config", type=str, required=True, help="Path to config .json file")
    args.add_argument("--task", type=str, required=True, help="Path to task description .json file")
    args.add_argument("--recalculate-results", type=str, default=None, help="all (solutions and terminated recalculated), unsolved (keep solutions, but retry terminated/unsuccessful), failed (keep solutions & terminated, retry unsuccessful), none (keep any attempts present, run on any new files)")
    args = args.parse_args()

    return args

def load_config(config_path):
    with open(config_path, 'r') as file:
        config = json.load(file)
    return config

def create_chat_clients(config):
    clients = []
    base_port = config.get('base_port', 11434)

    for i in range(config['gpus']):
        clients.append(ollama.Client(
            host="http://127.0.0.1:" + str(base_port + i),
            # timeout = httpx.Timeout(
            #     connect = config['ollama_connection_timeout'],
            #     read = config['query_timeout'],
            #     write = config['query_timeout'],
            #     pool = config['ollama_connection_timeout']
            # )
            timeout = None
        ))
    
    return clients

def load_task(task_path):
    with open(task_path, 'r') as file:
        task = json.load(file)

    return task

import os

def load_code(config):
    code_paths = config['input']
    code = []
    config['code_paths'] = []

    for code_path in code_paths:
        temp_paths = []

        if os.path.isdir(code_path):
            with os.scandir(code_path) as entries:
                temp_paths = [entry.path for entry in entries if entry.is_file()]
        else:
            temp_paths = [code_path]

        for path in temp_paths:
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
    #return sys.modules['preprocessor'].init()
def init_verifier(task_dir):
    load_components('verifier',f'{task_dir}/verify.py')
    #return sys.modules['verifier'].init()

def init_ollama(config):
    subprocess.run(['./start_ollama.sh', config], cwd=os.path.dirname(os.path.abspath(__file__)))
    print("Ollama Initialized")

def load_model_on_gpu(chat_clients, config, gpu, llm):
    base_port = config.get('base_port', 11434)
    while True:
        try:
            print(f"initializing model {llm} on {base_port+gpu}")
            response = chat_clients[gpu].chat(
                model = llm[0], 
                options = {'temperature' : llm[1]}, 
                messages=[{"role": "user", "content": "Hello World"}]
            )
            if response:
                print(f"SUCCESS - loaded model {llm[0]} w/ temperature {llm[1]} on gpu {gpu}")
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
        time.sleep(0.5)

def preload_model(clients, config, llm):
    port = config.get('base_port', 11434)
    env = os.environ.copy()
    env["OLLAMA_HOST"] = f"127.0.0.1:{port}"

    result = subprocess.run(
        ["ollama", "list"],
        capture_output=True,
        text=True,
        check=True,
        env=env
    )
    
    if llm[0] not in result.stdout:
        print(f"Pulling model {llm[0]}")
        subprocess.run(["ollama", "pull", llm[0]], check=True,env=env)

    with concurrent.futures.ThreadPoolExecutor(max_workers=config['gpus']) as executor:
        futures = [executor.submit(load_model_on_gpu, clients, config, gpu, llm) for gpu in range(config['gpus'])]
        concurrent.futures.wait(futures)
    
    print(f"Model {llm[0]} loaded on GPUs")