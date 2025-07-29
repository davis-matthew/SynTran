from transformers import AutoModelForCausalLM, AutoTokenizer
from peft import PeftModel
import subprocess
from pathlib import Path

script_dir = Path(__file__).resolve().parent

base_name = input("Base Model: ")
base_model = AutoModelForCausalLM.from_pretrained(base_name)
tokenizer = AutoTokenizer.from_pretrained(base_name)

peft_path = input("Fine-Tuning Peft: ")
peft_model = PeftModel.from_pretrained(base_model, peft_path)

output_path = input("Output Model Path: ")
merged = peft_model.merge_and_unload()

merged.save_pretrained(output_path)
tokenizer.save_pretrained(output_path)

model_name = input("Model Name: ")

subprocess.run(['bash', f'{script_dir}/add_model_to_ollama.sh', output_path, model_name])
