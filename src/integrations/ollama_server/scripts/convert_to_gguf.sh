#!/bin/sh
set -eu

SOURCE_MODEL_DIR="${1:-./deploy/models/cotype-nano}"
OUTPUT_GGUF="${2:-./src/integrations/ollama_server/models/cotype-nano-4bit.gguf}"

cat <<EOF
This project does not convert the model automatically.

Expected source model directory:
  ${SOURCE_MODEL_DIR}

Expected output GGUF:
  ${OUTPUT_GGUF}

Use a llama.cpp conversion workflow and place the resulting GGUF file into:
  ./src/integrations/ollama_server/models/

For LoRA adapters converted to Ollama GGUF adapters, use:
  ./src/integrations/ollama_server/scripts/build_ollama_lora_model.sh

Those artifacts are written to:
  ./deploy/gguf_adapters/
  ./deploy/modelfiles/

Then run:
  docker compose up -d ollama-server ollama-init
EOF
