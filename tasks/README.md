# Defining a New Translation Task:

A translation task consists of:
- a task description
- a set of preprocessing transformations
- a verifier that provides feedback

A template is provided in tasks/Template

## Task Description

A task description is defined in a file description.json and requires the following elements:

- prompts for the LLM
- input & output specification/tutorial

## Preprocessing Transformations

Preprocessing transformations are to be implemented in a file preprocess.py

The function preprocess is defined, which takes in the input code and returns a preprocessed form ready for LLM queries

## Verifier

Verifiers should be implemented in a file named verify.py

They must have 3 functions defined, verify_generation, verify_syntax, and verify_semantics, which each accept:
- the state information of the particular attempt
- a lock to use for synchronization across multiple threads attempting this problem
- the original src_code
- the most recently generated code from the LLM

These functions should return:
- a verdict (True = accepted, False = rejected)
- a status code string e.g. 'error_missing_semicolon' which will be used as a key to lookup the next prompt
- a feedback string such as an error message or other important information that may assist the model in repair of its attempt
