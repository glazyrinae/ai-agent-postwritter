#!/bin/sh
set -eu

usage() {
  cat <<'EOF'
Usage:
  build_ollama_lora_model.sh [adapter-name]

Behavior:
  - with no arguments: rebuild and re-register all adapters from deploy/lora_adapters/
  - with adapter-name: rebuild and re-register only that adapter

Requirements:
  - docker compose
  - running ollama-server service

This wrapper uses only containers:
  1. llama-converter container converts PEFT LoRA -> GGUF adapter
  2. ollama-server container removes old model entry and creates a new one
EOF
}

if [ "${1:-}" = "--help" ] || [ "${1:-}" = "-h" ]; then
  usage
  exit 0
fi

ROOT_DIR="$(CDPATH= cd -- "$(dirname "$0")/../../../.." && pwd)"
cd "${ROOT_DIR}"

OLLAMA_BASE_MODEL="${OLLAMA_BASE_MODEL:-hodza/cotype-nano-1.5-unofficial:latest}"

sanitize_name() {
  printf '%s' "$1" | tr '/: ' '___'
}

BASE_MODEL_NAME="$(sanitize_name "${OLLAMA_BASE_MODEL}")"

list_adapters() {
  if [ "${1:-}" != "" ]; then
    printf '%s\n' "$1"
    return
  fi

  find deploy/lora_adapters -mindepth 1 -maxdepth 1 -type d -printf '%f\n' | sort
}

if ! docker compose ps --status running --services | grep -qx 'ollama-server'; then
  echo "ollama-server is not running. Start it first with: docker compose up -d ollama-server" >&2
  exit 1
fi

ADAPTER_ARG="${1:-}"

echo "Running conversion inside llama-converter container..."
docker compose --profile tools run --rm \
  -e OLLAMA_BASE_MODEL="${OLLAMA_BASE_MODEL}" \
  llama-converter \
  sh -lc "src/integrations/ollama_server/scripts/build_ollama_lora_model_inner.sh ${ADAPTER_ARG}"

for adapter in $(list_adapters "${ADAPTER_ARG}"); do
  model_name="${BASE_MODEL_NAME}_${adapter}"
  modelfile="/workspace/deploy/modelfiles/${model_name}.Modelfile"

  echo "Re-registering ${model_name}"
  docker compose exec -T ollama-server ollama rm "${model_name}" >/dev/null 2>&1 || true
  docker compose exec -T ollama-server ollama create "${model_name}" -f "${modelfile}"
done

echo "Done."
