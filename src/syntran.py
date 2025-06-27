import json
import ollama
import subprocess
import os
import concurrent
import time
import threading
import sys
import setup

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

def preprocess(src):
    return sys.modules['preprocessor'].preprocess(src)

def verify(original_code_path, translated_code_path, report_path):
    return sys.modules['verifier'].verify(original_code_path, translated_code_path, report_path)

def save_translation(thread_id, problem_name, translation, attempts, status, current_task_time, current_thread_time):
    os.makedirs(f"{task['output']}/Chat{thread_id}", exist_ok=True)
    with open(f"{task['output']}/Chat{thread_id}/{problem_name}/Attempt{attempts}", 'w') as file:
        file.write(translation)
    
    if status == 'success':
        with open(f"{task['output']}/solution", 'w') as file:
            file.write(translation)
    if status == 'terminate':
        with open(f"{task['output']}/terminated", 'w') as file:
            file.write(translation)

def translation_thread(task_start_time, thread_start_time, thread_id, src, stop_event, RLSF = False):
    if not stop_event.is_set():
        generation_successful = generation_loop(task_start_time, thread_start_time, thread_id, src, stop_event, RLSF)
        if generation_successful:
            stop_event.set()
            return True
    return False

def generation_loop(thread_id, task_start_time, thread_start_time, src, stop_event, RLSF = False):
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
            os.makedirs(f"{task['output']}/Chat{thread_id}", exist_ok=True)
            with open(f"{task['output']}/Chat{thread_id}/temp_generation.txt", 'w') as file:
                file.write(translation)

            generation_timestamp = time.time()
            status, feedback = verify(thread_id)
            attempts += 1
            save_translation(thread_id, problem_name, translation, attempts, status, generation_timestamp - task_start_time, generation_timestamp - thread_start_time)
        except Exception as e:
            print(f"ERROR - failed to process chat request (exception: {e}) ... retrying")
    return status == 'success' or status == 'terminate'

def inference():
    global config
    global task
    global code
    global clients
    
    # Setup
    args = setup.parse_args()
    config = setup.load_config(args.config)
    clients = setup.create_clients(config)
    task = setup.load_task(args.task)
    code = setup.load_code(config)
    setup.init_preprocessor()
    setup.init_verifier()
    setup.init_ollama(config)    

    # Run
    stop_event = threading.Event()
    for llm in task['llms']:
        # Preload model to GPUs
        setup.preload_model(llm)

        for code_sample in code:
            code_sample = preprocess(code_sample)

            with open(f"{task['output']}/current_problem.txt",'w') as file:
                file.write(code_sample)
            
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
                                #TODO: save thread restarts separately instead of overwriting.
                                thread_id = futures.pop(future) 
                                futures[executor.submit(translation_thread, start_time, time.time(), thread_id, code_sample, stop_event)] = thread_id

                    if successful:
                        break

                    # Start up initial threads
                    if not futures:
                        futures = {executor.submit(translation_thread, start_time, time.time(), i, code_sample, stop_event): i for i in range(config['gpus'])}

                    time.sleep(0.1)  # Prevent tight looping

                stop_event.set()

            if successful:
                print("Finished")
            else:
                print("Unable to find a solution for the provided code")

inference()