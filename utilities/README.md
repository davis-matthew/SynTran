# Utilities:

### Flatten Prompt
For prepping the prompt to json format (single line, separated by \n), you can use the flatten_prompt_data script. This is helpful for converting online documentation to a prompt.

```
./flatten_prompt_data.sh input.file output.file
```

### Convert a basemodel and finetuning to ollama-ready model
After performing local training or finetuning of a model, the conversion to a ollama usable model is essential for using the inference loop in parallel across the available GPUs. This can be done with 
```python ./convert_basemodel_and_finetuning_to_ollama.py```