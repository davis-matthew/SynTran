def verify_generation(state, lock, src_code, generation):
    # Explanation of parameters:
    
    # state = thread-local modifiable dictionary to hold data
    # by-default contains:
    # {
    #   'problem_name'              - basename of the input file (without extension)
    #   'src_file'                  - path to the input file
    #
    #   'thread_id'                 - ID of the thread (for this problem)
    #   'llm_triple'                - LLM triple ({generation LLM name}-temp{generation LLM temp}##{syntax repair LLM name}-temp{syntax repair LLM temp}##{semantic repair LLM name}-temp{semantic repair LLM temp})
    #   'task_start_time'           - time.time() of when we started this problem
    #   'thread_start_time'         - time.time() of when this thread was started
    #
    #   'stats' :                   
    #   {
    #       'generations'           - # of generation queries total
    #       'syntactic_repairs'     - # of syntactic repair queries total
    #       'semantic_repairs'      - # of semantic repair queries total
    #       'queries'               - # of LLM queries total
    #   }
    #
    #   'overall_attempt'           - which attempt # is this?
    #   'generation_attempt'        - which generation attempt # is this?
    #   'syntactic_repair_attempt'  - which syntactic repair attempt is this?
    #   'semantic_repair_attempt'   - which semantic repair attempt # is this?
    #
    #   'message_log'               - dictionary of current messages (updates after each stage: generation, syntax repair, semantic repair)
    # }

    # lock = threading.Lock() shared by all threads currently working on this particular input

    # src_code = the original input asked to be translated

    # generation = the current content of the translation process 
    pass

def verify_syntax(state, lock, src_code, generation):
    # Possible verification results:

    # All checks passed - ready to move onto repair
    if verified:
        return True, 'success', 'verification message'
    
    # Verification failed 
    if error:
        return False, 'error type (maps to a prompt in description.json)', 'feedback'

    # This problem is impossible - This could be an unimplemented part of the problem or you just want to skip it
    if terminate:
        return None, 'terminate', 'termination message'

def verify_semantics(state, lock, src_code, generation):
    pass