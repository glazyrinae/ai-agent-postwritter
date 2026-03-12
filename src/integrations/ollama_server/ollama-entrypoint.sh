#!/bin/sh
set -eu

MODEL_NAME="${OLLAMA_MODEL_NAME:-hodza/cotype-nano-1.5-unofficial}"
WORKDIR="/workspace/ollama_server"
MODELFILE="${OLLAMA_LOCAL_MODELFILE:-/workspace/deploy/modelfiles/Modelfile}"
GGUF_PATH="${WORKDIR}/models/cotype-nano-4bit.gguf"

echo "Waiting for Ollama API..."
tries=0
until OLLAMA_HOST="${OLLAMA_HOST:-http://ollama-server:11434}" ollama list >/dev/null 2>&1; do
  tries=$((tries + 1))
  if [ "$tries" -ge 60 ]; then
    echo "Ollama API is not reachable."
    exit 1
  fi
  sleep 2
done

if [ ! -f "$GGUF_PATH" ]; then
  echo "GGUF file not found at $GGUF_PATH"
  echo "Falling back to direct ollama pull for ${MODEL_NAME}"
  OLLAMA_HOST="${OLLAMA_HOST:-http://ollama-server:11434}" ollama pull "$MODEL_NAME"
  OLLAMA_HOST="${OLLAMA_HOST:-http://ollama-server:11434}" ollama list
  exit 0
fi

if [ ! -f "$MODELFILE" ]; then
  echo "Modelfile not found at $MODELFILE"
  exit 1
fi

OLLAMA_HOST="${OLLAMA_HOST:-http://ollama-server:11434}" ollama create "$MODEL_NAME" -f "$MODELFILE"
OLLAMA_HOST="${OLLAMA_HOST:-http://ollama-server:11434}" ollama list
