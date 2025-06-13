import json
import argparse
import ollama
import subprocess
import os
import concurrent
import time

# Syntran Design:
#
# ------------------------------------------------------------------------
#                  Task Definition
#                         |
#                         v
# input -> preprocess -> LLM        ---->      verifier     ---->   output
#                         ^                        |
#                         |                        v
#                        RLSF*      <----  symbolic feedback
# ------------------------------------------------------------------------
# * - RLSF is enabled during fine-tuning, but disabled for inference
#

config = None
task = None
code = None
clients = None

def load_config(config_path):
    global config
    global clients
    with open(config_path, 'r') as file:
        config = json.load(file)
    clients = [None] * config['gpus']

def load_task(task_path):
    global task
    with open(task_path, 'r') as file:
        task = json.load(file)
    task['prompts']['system'] = task['prompts']['system'].replace('+SPEC_INPUT+', task['specifications']['input']).replace('+SPEC_OUTPUT+', task['specifications']['output'])

def load_code(code_paths):
    global code
    code = []
    for code_path in code_paths:
        with open(code_path, 'r') as file:
            code.append(preprocess(file.read()))

def load_gpu(gpu):
    global clients
    port = 11434
    while True:
        try:
            print(f"initializing model on {port+gpu}")
            clients[gpu] = ollama.Client(host="http://127.0.0.1:"+str(port+gpu), timeout = 300)
            response = clients[gpu].chat(
                model=task['llm'], 
                messages=[{"role": "system", "content": "Initializing model"}]
            )
            if response:
                print(f"SUCCESS - loaded model on gpu {gpu}")
                return True
            else:
                print(f"ERROR - failed to load model on gpu")
        except Exception as e:
            print(f"ERROR - failed to load model on gpu (could not send request) - {e}")
        time.sleep(0.1) # Prevent tight looping

def preprocess(src):
    return src #identity transformation
    #task['preprocessing']

def save_translation(thread_id, translation, attempts, status, current_time):
    with open(f"{task['output']}/Chat{thread_id}/Attempt{attempts}") as file: #FIXME: add code file prefix
        file.write(translation)
    
    if status == 'success':
        with open(f"{task['output']}/solution") as file:
            file.write(translation)

def translation_thread(task_start_time, thread_start_time, thread_id, src, RLSF = False):
    if not stop_event.is_set():
        generation_successful = generation_loop(task_start_time, thread_start_time, thread_id, src, RLSF)
        if generation_successful:
            stop_event.set()
            return True
    return False

def generation_loop(thread_id, task_start_time, thread_start_time, src, RLSF = False):
    status = 'translation'
    feedback = src
    attempts = 0
    messages = [{"role": "system", "content": task['prompts']['system']}]

    while   not status == 'success' \
            and attempts <= config['attempts_per_chat'] \
            and not stop_event.is_set():

        messages.append({"role": "user", "content" : task['prompts'][status].replace("+FEEDBACK+",feedback)})
        try:
            response = ollama.chat(model=task['llm'], messages=messages)
            translation = response['message']['content']
            generation_timestamp = time.time()
            status, feedback = verify(translation)
            attempts += 1
            save_translation(thread_id, translation, attempts, status, generation_timestamp - task_start_time, generation_timestamp - thread_start_time)
        except Exception as e:
            print(f"ERROR - failed to process chat request (exception: {e}) ... retrying")

    return status == 'success'

def verify():
    #TODO: implement
    #task['verifier']
    return True

def run():
    # Setup
    args = argparse.ArgumentParser(description="command-line flag parser")
    args.add_argument("--config", type=str, required=True, help="Path to config .json file")
    args.add_argument("--task", type=str, required=True, help="Path to task description .json file")
    args.add_argument("code", nargs='*', help="input code file(s)")
    args = args.parse_args()

    load_config(args.config)
    load_task(args.task)
    load_code(args.code)

    # Start ollama
    print(os.path.dirname(os.path.abspath(__file__)))
    subprocess.run(['./start_ollama.sh', args.config], cwd=os.path.dirname(os.path.abspath(__file__)))
    print("Ollama started, loading models")

    # Preload model to GPUs
    with concurrent.futures.ThreadPoolExecutor(max_workers=config['gpus']) as executor:
        futures = [executor.submit(load_gpu, gpu) for gpu in range(config['gpus'])]
        concurrent.futures.wait(futures)

    # Run
    #for llm in task['llms']: # FIXME: We'd like to be able to iterate over the llms
        for code_sample in code:
            successful = False
            start_time = time.time()
            with concurrent.futures.ThreadPoolExecutor(max_workers=config['gpus']) as executor:
                futures = {}

                while time.time() - start_time < config['timeout']:
                    # Restart unsuccessful threads who reached attempt max
                    for future in list(futures):
                        if future.done():
                            if future.result(): # Successful translation
                                successful = True
                                stop_event.set()
                                break
                                
                            if not stop_event.is_set(): # Restart the chat
                                thread_id = futures.pop(future)
                                futures[executor.submit(translation_thread, start_time, time.time(), thread_id, code_sample)] = thread_id

                    if successful:
                        break

                    # Start up initial threads
                    if not futures:
                        futures = {executor.submit(translation_thread, start_time, time.time(), i, code_sample): i for i in range(config['gpus'])}

                    time.sleep(0.1)  # Prevent tight looping

                stop_event.set()

            if successful:
                print("Success")

run()