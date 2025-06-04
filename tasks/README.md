# Defining a New Translation Task:

A translation task consists of:
- a task description
- a set of preprocessing transformations
- an oracle feedback provider
- dataset(s) corresponding to the problem. 

## Task Description

A task description requires the following elements:

- prompt for the LLM
- input specification/tutorial
- output specification/tutorial

## Preprocessing Transformations

A set of preprocessing transformations consists of a schedule of transformations to run

## Oracle Feedback Provider

An oracle is a piece of software (e.g. solver, program analysis, compiler, etc.) which relays a verdict on the generated translation.

## Dataset

A dataset is a list of tests to compare the translation generations against.