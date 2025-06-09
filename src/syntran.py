import json
import argparse
import ollama

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

config = None
task = None
code = None
clients = None

def load_config(config_path):
    global config
    with open(config_path, 'r') as file:
        config = json.load(file)

def load_task(task_path):
    global task
    with open(task_path, 'r') as file:
        task = json.load(file)
    task['prompts']['system'] = task['prompts']['system'].replace('+SPEC_INPUT+', task['specifications']['input']).replace('+SPEC_OUTPUT+', task['specifications']['output'])

def load_code(code_path):
    global code
    with open(code_path, 'r') as file:
        code = file.read()
    code = preprocess(code)

def load_gpu(gpu):
    port = 11434
    while True:
        try:
            clients[gpu] = ollama.Client(host="http://127.0.0.1:"+str(port+gpu), timeout = 300)
            response = clients[gpu].chat(
                model=config['llm'], 
                messages=[{"role": "system", "content": "Initializing model"}]
            )
            if response:
                print(f"SUCCESS - loaded model on gpu {gpu}")
                return True
            else:
                print(f"ERROR - failed to load model on gpu")
        except:
            print(f"ERROR - failed to load model on gpu (could not send request)")

def preprocess(src):
    return src #identity transformation
    #task['preprocessing']

def save_translation(thread_id, translation, attempts, status, current_time):
    with open(f"{task['output']}/Chat{thread_id}/Attempt{attempts}") as file:
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
    subprocess.run(['start_ollama.sh', args.config])

    # Preload model to GPUs
    with concurrent.futures.ThreadPoolExecutor(max_workers=config['gpus']) as executor:
        futures = [executor.submit(load_gpu, gpu) for gpu in range(config['gpus'])]
        concurrent.futures.wait(futures)

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
                        futures[executor.submit(translation_thread, start_time, time.time(), thread_id, preprocessed_code)] = thread_id

            if successful:
                break

            # Start up initial threads
            if not futures:
                futures = {executor.submit(translation_thread, start_time, time.time(), i, preprocessed_code): i for i in range(config['gpus'])}

            time.sleep(0.1)  # Prevent tight looping

        stop_event.set()

    if successful:
        print("Success")
    
    return successful

run()