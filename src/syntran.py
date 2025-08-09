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

config = None
task = None
code = None
chat_clients = None
lock = threading.Lock()

def preprocess(src):
    return sys.modules['preprocessor'].preprocess(src)
def verify_generation(state, lock, src_code, generation):
    return sys.modules['verifier'].verify_generation(state, lock, src_code, generation)
def verify_syntax(state, lock, src_code, generation):
    return sys.modules['verifier'].verify_syntax(state, lock, src_code, generation)
def verify_semantics(state, lock, src_code, generation):
    return sys.modules['verifier'].verify_semantics(state, lock, src_code, generation)

def generate_llm_triple_string(llm_triple):
    return "##".join(
        f"{model}-temp{temp}" for _, (model, temp) in llm_triple.items()
    )


def prompt_variable_replacement(prompt, src, generation, feedback = ''):
    return prompt.replace("+SPEC_INPUT+",   task['specifications']['input'])\
                .replace("+SPEC_OUTPUT+",   task['specifications']['output'])\
                .replace("+SRC_CODE+",      src)\
                .replace("+GENERATION+",    generation)\
                .replace("+FEEDBACK+",      feedback)

def query(state, query_type, messages):
    model = state['llm_triple'][query_type]
    model_name = model[0]
    model_temperature = model[1]

    response = chat_clients[state['thread_id']].chat(
        model = model_name,
        options = {"temperature" : model_temperature},
        messages = messages
    )
    state['query_timestamp'] = time.time()
    return response.message.content

def save_translation(state, src_code, generation, verification_success, result, feedback):
    output_path = f"{config['output']}/{generate_llm_triple_string(state['llm_triple'])}/{state['problem_name']}"
    os.makedirs(output_path, exist_ok=True)
    os.makedirs(f"{output_path}/Chat{state['thread_id']}", exist_ok=True)
    with open(f"{output_path}/Chat{state['thread_id']}/Attempt{state['overall_attempt']}-{state['generation_attempt']}-{state['semantic_repair_attempt']}-{state['syntactic_repair_attempt']}", 'w') as file:
        file.write(generation + "\n\n\n---Feedback---\n" + feedback)
    
    if verification_success == 'success':
        with open(f"{output_path}/solution", 'w') as file:
            file.write(generation + "\n\n\n---Feedback---\n" + feedback)
    if result == 'terminate':
        with open(f"{output_path}/terminated", 'w') as file:
            file.write(generation + "\n\n\n---Feedback---\n" + feedback)

def translation_thread(
        thread_id, 
        llm_triple, 
        problem_name, src_file, src_code, 
        task_start_time, thread_start_time,  
        stop_event):
    

    if not stop_event.is_set():
        state = {
            'problem_name'      : problem_name,
            'src_file'          : src_file,
            
            'thread_id'         : thread_id,
            'llm_triple'        : llm_triple,
            'task_start_time'   : task_start_time,
            'thread_start_time' : thread_start_time
        }

        generation_successful = generation_loop(state, src_code, stop_event)
        if generation_successful:
            stop_event.set()
            return True
    return False

def generation_loop(state, src_code, stop_event):
    state['overall_attempt'] = 0
    state['generation_attempt'] = 0
    state['syntactic_repair_attempt'] = 0
    state['semantic_repair_attempt'] = 0

    state['message_log'] = []

    verification_success = False

    while not stop_event.is_set():
        state['message_log'].append({})
        restart_attempt = False
        terminate = False
        generation = ""
        feedback = ""

        # Initial Generation
        state['generation_attempt'] = 0        
        messages = [{'role': 'system',  'content': prompt_variable_replacement(task['prompts']['generation']['system'], src_code, generation)}]
        generation_result = 'generation'

        while True:
            if state['generation_attempt'] >= config['chat_generation_attempts']:
                restart_attempt = True
                break

            messages.append({'role': 'user', 'content': prompt_variable_replacement(task['prompts']['generation'][generation_result], src_code, generation, feedback)})
            
            try:
                generation = query(state, 'generation', messages)                
                messages.append({'role': 'assistant', 'content': generation})
                verification_success, generation_result, feedback = verify_generation(state, lock, src_code, generation)
                save_translation(state, src_code, generation, verification_success, generation_result, feedback)
                
            except Exception as e:
                e = str(e)
                if "Access Denied" in e or "ERR_ACCESS_DENIED" in e:
                    print("ERROR - Access Denied. Try unsetting http_proxy and https_proxy")
                else:
                    print(f"ERROR - failed to process chat request (exception: {e})")
                    traceback.print_exc()
                exit(1)
            
            state['generation_attempt'] += 1
            if generation_result == 'terminate':
                terminate = True
                break

            if verification_success:
                break

        state['message_log'][-1]['generation'] = messages
        
        if terminate:
            break

        if restart_attempt:
            continue

        # Repair Generation
        state['semantic_repair_attempt'] = 0
        state['message_log'][-1]['repair'] = []

        syntactic_repair_result = ""
        semantic_repair_result = ""
        
        while True:
            state['message_log'][-1]['repair'].append({})

            if state['semantic_repair_attempt'] > config['chat_semantic_repair_attempts']:
                restart_attempt = True
                break

            # Syntactic Repair
            state['syntactic_repair_attempt'] = 0
            messages = [{'role': 'system',  'content': prompt_variable_replacement(task['prompts']['syntactic_repair']['system'], src_code, generation)}]

            while True:
                if state['syntactic_repair_attempt'] > config['chat_syntactic_repair_attempts']:
                    restart_attempt = True
                    break
                
                verification_success, syntactic_repair_result, feedback = verify_syntax(state, lock, src_code, generation)
                messages.append({'role': 'user', 'content': prompt_variable_replacement(task['prompts']['syntactic_repair'][syntactic_repair_result], src_code, generation, feedback)})
                save_translation(state, src_code, generation, verification_success, generation_result, feedback)
                
                if verification_success:
                    break

                if syntactic_repair_result == 'terminate':
                    terminate = True
                    break

                generation = query(state, 'syntactic_repair', messages)
                messages.append({'role': 'assistant', 'content' : generation})
                state['syntactic_repair_attempt'] += 1
            
            state['message_log'][-1]['repair'][-1]['syntactic_repair'] = messages
            if terminate or restart_attempt:
                break

            verification_success, semantic_repair_result, feedback = verify_semantics(state, lock, src_code, generation)
            messages = [{'role': 'user', 'content': prompt_variable_replacement(task['prompts']['semantic_repair'][semantic_repair_result], src_code, generation, feedback)}]
            save_translation(state, src_code, generation, verification_success, generation_result, feedback)
            
            if verification_success:
                break
            
            if semantic_repair_result == 'terminate':
                terminate = True
                break

            generation = query(state, 'semantic_repair', messages)
            messages.append({'role': 'assistant', 'content' : generation})
            state['semantic_repair_attempt'] += 1
            state['message_log'][-1]['repair'][-1]['semantic_repair'] = messages
        
        state['overall_attempt'] += 1

        if terminate:
            break

    if terminate:
        stop_event.set()
        print("attempt terminated")
        
    return verification_success

def finetune():
    #TODO : IMPLEMENT
    pass

def inference():
    global config
    global task
    global code
    global chat_clients
    
    # Setup
    args = setup.parse_args()
    config = setup.load_config(args.config)
    task = setup.load_task(args.task)
    code = setup.load_code(config)
    setup.init_preprocessor(os.path.dirname(args.task))
    setup.init_verifier(os.path.dirname(args.task))
    setup.init_ollama(args.config)
    chat_clients = setup.create_chat_clients(config)
    os.makedirs(config['output'], exist_ok=True)

    # Run
    for triple_id, llm_triple in enumerate(config['llms']):
        # Preload generation model to GPUs
        setup.preload_model(chat_clients, config, llm_triple['generation'])

        for idx in range(len(code)):
            stop_event = threading.Event()
            code_file = config['code_paths'][idx]
            code_sample = preprocess(code[idx])
            problem_name = os.path.splitext(os.path.basename(code_file))[0]
            print(f'Starting {problem_name} w/ LLM Triple: {generate_llm_triple_string(llm_triple).replace("##", " | ")}')
            folder = pathlib.Path(f"{config['output']}/{generate_llm_triple_string(llm_triple)}/{problem_name}")
            args.recalculate_results = args.recalculate_results or 'none'
            
            if args.recalculate_results == 'none':
                pass
            elif args.recalculate_results == 'all':
                if folder.exists():
                    shutil.rmtree(folder)
            elif args.recalculate_results == 'unsolved':
                if folder.exists() and not (folder / 'solution').exists():
                    shutil.rmtree(folder)
            elif args.recalculate_results == 'failed':
                if folder.exists() and not (folder / 'solution').exists() and not (folder / 'terminated').exists():
                    shutil.rmtree(folder)
            else:
                print(f"Unrecognized recalculate results option {args.recalculate_results}. Quitting")
                exit(0)

            if folder.exists():
                print(f"{problem_name} result already exists... skipping\n")
                continue


            # with open(f"{config['output']}/current_problem.txt",'w') as file:
            #     file.write(code_sample) 
            
            successful = False
            start_time = time.time()
            with concurrent.futures.ThreadPoolExecutor(max_workers=config['gpus']) as executor:
                futures = {}

                while time.time() - start_time < config['task_timeout'] and not stop_event.is_set():
                    # Restart unsuccessful threads who reached attempt max
                    for future in list(futures):
                        if future.done():
                            if future.result(): # Successful translation
                                successful = True
                                stop_event.set()
                                break
                    if successful:
                        break

                    # Start up initial threads
                    if not futures:
                        futures = {executor.submit(translation_thread, i, llm_triple, problem_name, code_file, code_sample, start_time, time.time(), stop_event): i for i in range(config['gpus'])}
                    time.sleep(0.1)  # Prevent tight looping

                stop_event.set()

            if successful:
                print(f"Finished {problem_name}\n")
            else:
                print("Unable to find a solution for the provided code\n")

inference()