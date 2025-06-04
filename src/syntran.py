import json
import argparse
import requests

# New-Tool Design:
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

def load_config(config_path):
    with open(config_path, 'r') as file:
        config = json.load(file)
    return config

def load_gpu(gpu):
    port = 11434
    preload = {"model": config['llm']}
    while True:
        try:
            response = requests.post(f"http://localhost:{(port+gpu)}/api/chat", json=preload)
            if response.status_code == 200:
                print(f"SUCCESS - loaded model on gpu {gpu}")
                return True
            else:
                print(f"ERROR - failed to load model on gpu: {response.text} error code {response.status_code} ... retrying")
        except:
            print(f"ERROR - failed to load model on gpu (could not send request) ... retrying")

def load_task(task_path):
    with open(task_path, 'r') as file:
        task = json.load(file)
    return task

def preprocess(src):
    return src #identity transformation
    #task['preprocessing']

def translation_thread(thread_id, src, RLSF = False):
    port = 11434
    gpu = f'http://localhost:{(port+thread_id)}/api/chat'
    
    if not stop_event.is_set() and generation_loop(thread_id, src, gpu, RLSF):
        stop_event.set()
        return True

def generation_loop(thread_id, src, gpu, RLSF = False):
    status = 'translation'
    feedback = src
    attempts = 0
    messages = [{"role": "system", "content": task['prompts']['system']}]

    while   not status == 'success' \
            and attempts <= config['attempts_per_chat'] \
            and not stop_event.is_set():

        messages.append({"role": "user", "content" : task['prompts'][status].replace("+FEEDBACK+",feedback)})
        translation = requests.post(gpu, 
                        json={"model" : task['llm'], "messages" : messages}, 
                        timeout=config['per_query_timeout']
                    ).json()['message']['content']
        status, feedback = verify(translation)
        attempts += 1
        save_translation(thread_id, translation, attempts, status)

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

    config = load_config(args.config)

    # Start ollama
    subprocess.run(['start_ollama.sh', args.config])

    # Preload model to GPUs
    with concurrent.futures.ThreadPoolExecutor(max_workers=config['gpus']) as executor:
        futures = [executor.submit(load_gpu, gpu) for gpu in range(config['gpus'])]
        concurrent.futures.wait(futures)
    
    task = load_task(args.task)
    task['prompts']['system'] = task['prompts']['system'].replace('+SPEC_INPUT+', task['specifications']['input']).replace('+SPEC_OUTPUT+', task['specifications']['output'])

    code = load_code(args.code)
    preprocessed_code = preprocess(code)

    # Run
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
                        futures[executor.submit(translation_thread, thread_id, preprocessed_code)] = thread_id

            if successful:
                break

            # Start up initial threads
            if not futures:
                futures = {executor.submit(translation_thread, i, preprocessed_code): i for i in range(config['gpus'])}

            time.sleep(0.1)  # Prevent tight looping

        stop_event.set()

    if successful:
        print("Success")
    
    return successful

run()