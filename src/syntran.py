import ollama
import os
import concurrent
import time
import threading
import sys
import setup
import traceback
import pathlib
import shutil

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

#TODO-s:
# 1. Allow for skipping a test file if a result is already generated
# 2. Check verification

config = None
task = None
code = None
chat_clients = None

def preprocess(src):
    return sys.modules['preprocessor'].preprocess(src)

def verify(original_code_path, translated_code_path):
    return sys.modules['verifier'].verify(original_code_path, translated_code_path)

def save_translation(thread_id, problem_name, translation, attempts, status, current_task_time, current_thread_time):
    output_path = f"{config['output']}/{problem_name}/Chat{thread_id}"
    os.makedirs(output_path, exist_ok=True)
    with open(f"{output_path}/Attempt{attempts}", 'w') as file:
        file.write(translation)
    
    if status == 'success':
        with open(f"{config['output']}/{problem_name}/solution", 'w') as file:
            file.write(translation)
    if status == 'terminate':
        with open(f"{config['output']}/{problem_name}/terminated", 'w') as file:
            file.write(translation)

def translation_thread(
        thread_id, 
        llm, 
        problem_name, src_file, src_code, 
        task_start_time, thread_start_time,  
        stop_event):
    
    if not stop_event.is_set():
        generation_successful = generation_loop(thread_id, llm, problem_name, src_file, src_code, task_start_time, thread_start_time, stop_event)
        if generation_successful:
            stop_event.set()
            return True
    return False

def generation_loop(
        thread_id, 
        llm, 
        problem_name, src_file, src_code, 
        task_start_time, thread_start_time,  
        stop_event):
    
    status = 'translation'
    feedback = src_code
    attempts = 0
    messages = [{"role": "system", "content": task['prompts']['system']}]
    output_path = f"{config['output']}/{problem_name}/Chat{thread_id}"
    os.makedirs(output_path, exist_ok=True)

    while   not status == 'success' \
            and not status == 'terminate' \
            and attempts <= config['attempts_per_chat'] \
            and not stop_event.is_set():

        messages.append({"role": "user", "content" : task['prompts'][status].replace("+FEEDBACK+",feedback)})
        try:
            response = ollama.chat(model=llm, messages=messages)
            translation = response['message']['content']
            messages.append({
                "role": "assistant",
                "content": translation
            })
            
            with open(f"{output_path}/temp_generation.txt", 'w') as file:
                file.write(translation)

            generation_timestamp = time.time()
            status, feedback = verify(src_file, f"{output_path}/temp_generation.txt")
            attempts += 1
            save_translation(thread_id, problem_name, translation, attempts, status, generation_timestamp - task_start_time, generation_timestamp - thread_start_time)
        
        except Exception as e:
            e = str(e)
            if "Access Denied" in e or "ERR_ACCESS_DENIED" in e:
                print("ERROR - Access Denied. Removing http_proxy and https_proxy and retrying")
                os.environ.pop("http_proxy", None)
                os.environ.pop("https_proxy", None)
                time.sleep(0.5) # Prevent tight looping
            else:
                print(f"ERROR - failed to process chat request (exception: {e}) ... retrying")
                traceback.print_exc()
    with open(f"{output_path}/chatlog.txt", 'w') as file:
        file.write(str(messages))
    return status == 'success' or status == 'terminate'

def finetune():
    global config
    global task
    global code
    global chat_clients

    # Setup
    args = setup.parse_args()
    config = setup.load_config(args.config)
    chat_clients = setup.create_chat_clients(config)
    task = setup.load_task(args.task)
    code = setup.load_code(config)
    setup.init_preprocessor()
    setup.init_verifier()
    setup.init_ollama(config)

    #TODO : FIXME

def inference():
    global config
    global task
    global code
    global chat_clients
    
    # Setup
    args = setup.parse_args()
    config = setup.load_config(args.config)
    chat_clients = setup.create_chat_clients(config)
    task = setup.load_task(args.task)
    code = setup.load_code(config)
    setup.init_preprocessor(os.path.dirname(args.task))
    setup.init_verifier(os.path.dirname(args.task))
    setup.init_ollama(args.config)
    os.makedirs(config['output'], exist_ok=True)

    # Run
    for llm in config['llms']:
        # Preload model to GPUs
        setup.preload_model(config, llm)

        for idx in range(len(code)):
            stop_event = threading.Event()
            code_file = config['code_paths'][idx]
            code_sample = preprocess(code[idx])
            problem_name = os.path.splitext(os.path.basename(code_file))[0]
            restart_counts = {}
            print(f'Starting {problem_name} w/ LLM {llm}')

            folder = pathlib.Path(f"{config['output']}/{problem_name}")
            if not (args.recalculate_results is None or args.recalculate_results == 'none'):
                if args.recalculate_results == 'all':
                    if folder.exists():
                        shutil.rmtree(folder)
                elif args.recalculate_results == 'terminated':
                    if (folder / 'terminated').exists():
                        shutil.rmtree(folder)
                else:
                    print("unrecognized recalculate results option... skipping")
            else:
                if folder.exists():
                    print(f"\t{problem_name} result already exists... skipping")
                    continue

            with open(f"{config['output']}/current_problem.txt",'w') as file:
                file.write(code_sample) 
            
            successful = False
            start_time = time.time()
            with concurrent.futures.ThreadPoolExecutor(max_workers=config['gpus']) as executor:
                futures = {}

                while time.time() - start_time < config['task_timeout']:
                    # Restart unsuccessful threads who reached attempt max
                    for future in list(futures):
                        if future.done():
                            if future.result(): # Successful translation
                                successful = True
                                stop_event.set()
                                break
                                
                            if not stop_event.is_set(): # Restart the chat
                                thread_id = futures.pop(future)
                                restart_counts[thread_id] += 1
                                futures[executor.submit(translation_thread, f"{thread_id}_restart{restart_counts[thread_id]}", llm, problem_name, code_file, code_sample, start_time, time.time(), stop_event)] = thread_id

                    if successful:
                        break

                    # Start up initial threads
                    if not futures:
                        futures = {executor.submit(translation_thread, i, llm, problem_name, code_file, code_sample, start_time, time.time(), stop_event): i for i in range(config['gpus'])}
                        for i in range(config['gpus']):
                            restart_counts[i] = 0
                    time.sleep(0.1)  # Prevent tight looping

                stop_event.set()

            if successful:
                print(f"Finished {problem_name}\n")
            else:
                print("Unable to find a solution for the provided code")

inference()