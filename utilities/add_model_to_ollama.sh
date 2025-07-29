OUT=$1
NAME=$2

SCRIPT_PATH="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

module load ollama
# if ! curl -s http://localhost:11434/ > /dev/null; then
#   echo "Starting Ollama server..."
#   nohup ollama serve > /dev/null 2>&1 &
#   sleep 2  # Give it a moment to start
# fi

ollama rm $NAME
python3 $SCRIPT_PATH/llama.cpp_convert_hf_to_gguf.py $SCRIPT_PATH/$OUT # Taken from llama.cpp


# FIXME: this sed command does not work.
sed -i "s/\[MODEL\]/$OUT/g" $SCRIPT_PATH/Modelfile
ollama create $NAME -f $SCRIPT_PATH/Modelfile