#!/bin/sh
set -eu

usage() {
  cat <<'EOF'
Usage:
  build_ollama_lora_model_inner.sh [adapter-name]

This script is intended to run inside the llama-converter container.
It converts PEFT LoRA adapters to GGUF and writes generated Modelfiles.
EOF
}

if [ "${1:-}" = "--help" ] || [ "${1:-}" = "-h" ]; then
  usage
  exit 0
fi

ROOT_DIR="$(CDPATH= cd -- "$(dirname "$0")/../../../.." && pwd)"
LLAMA_CPP_DIR="${LLAMA_CPP_DIR:-/opt/llama.cpp}"
if [ "${CONVERTER_PYTHON:-}" = "" ]; then
  if [ -x "/opt/venv/bin/python" ]; then
    CONVERTER_PYTHON="/opt/venv/bin/python"
  else
    CONVERTER_PYTHON="python3"
  fi
fi
BASE_MODEL_CONFIG_DIR="${BASE_MODEL_CONFIG_DIR:-${ROOT_DIR}/deploy/models/cotype-nano}"
OLLAMA_BASE_MODEL="${OLLAMA_BASE_MODEL:-hodza/cotype-nano-1.5-unofficial:latest}"

ADAPTERS_ROOT="${ROOT_DIR}/deploy/lora_adapters"
OUTPUT_DIR="${ROOT_DIR}/deploy/gguf_adapters"
GENERATED_DIR="${ROOT_DIR}/deploy/modelfiles"
TMP_BASE_DIR="$(mktemp -d)"

cleanup() {
  rm -rf "${TMP_BASE_DIR}"
}
trap cleanup EXIT INT TERM

if [ ! -f "${LLAMA_CPP_DIR}/convert_lora_to_gguf.py" ]; then
  echo "llama.cpp converter not found: ${LLAMA_CPP_DIR}/convert_lora_to_gguf.py" >&2
  exit 1
fi

if ! "${CONVERTER_PYTHON}" -c "import transformers, torch, gguf" >/dev/null 2>&1; then
  cat >&2 <<EOF
Converter dependencies are not available for ${CONVERTER_PYTHON}.
This container must provide transformers, torch and gguf.
EOF
  exit 1
fi

mkdir -p "${OUTPUT_DIR}" "${GENERATED_DIR}"
cp "${BASE_MODEL_CONFIG_DIR}/config.json" "${TMP_BASE_DIR}/"
[ -f "${BASE_MODEL_CONFIG_DIR}/tokenizer.json" ] && cp "${BASE_MODEL_CONFIG_DIR}/tokenizer.json" "${TMP_BASE_DIR}/"
[ -f "${BASE_MODEL_CONFIG_DIR}/tokenizer_config.json" ] && cp "${BASE_MODEL_CONFIG_DIR}/tokenizer_config.json" "${TMP_BASE_DIR}/"
[ -f "${BASE_MODEL_CONFIG_DIR}/generation_config.json" ] && cp "${BASE_MODEL_CONFIG_DIR}/generation_config.json" "${TMP_BASE_DIR}/"
[ -f "${BASE_MODEL_CONFIG_DIR}/chat_template.jinja" ] && cp "${BASE_MODEL_CONFIG_DIR}/chat_template.jinja" "${TMP_BASE_DIR}/"

TMP_BASE_DIR="${TMP_BASE_DIR}" "${CONVERTER_PYTHON}" - <<'PY'
import json
import os
from pathlib import Path

cfg_path = Path(os.environ["TMP_BASE_DIR"]) / "config.json"
cfg = json.loads(cfg_path.read_text())
for key in ("quantization_config", "torch_dtype"):
    cfg.pop(key, None)
cfg["_name_or_path"] = cfg.get("_name_or_path") or "MTSAIR/Cotype-Nano"
cfg_path.write_text(json.dumps(cfg, ensure_ascii=False, indent=2))
PY

sanitize_name() {
  printf '%s' "$1" | tr '/: ' '___'
}

BASE_MODEL_NAME="$(sanitize_name "${OLLAMA_BASE_MODEL}")"

process_adapter() {
  ADAPTER_NAME="$1"
  ADAPTER_DIR="${ADAPTERS_ROOT}/${ADAPTER_NAME}"
  OUTPUT_GGUF="${OUTPUT_DIR}/${ADAPTER_NAME}-lora.gguf"
  OLLAMA_MODEL_NAME="${BASE_MODEL_NAME}_${ADAPTER_NAME}"
  MODELFILE_PATH="${GENERATED_DIR}/${OLLAMA_MODEL_NAME}.Modelfile"

  if [ ! -d "${ADAPTER_DIR}" ] || [ ! -f "${ADAPTER_DIR}/adapter_config.json" ]; then
    echo "Skipping ${ADAPTER_NAME}: adapter_config.json not found" >&2
    return 0
  fi

  echo "Converting adapter '${ADAPTER_NAME}' to ${OUTPUT_GGUF}"
  rm -f "${OUTPUT_GGUF}" "${MODELFILE_PATH}"
  "${CONVERTER_PYTHON}" "${LLAMA_CPP_DIR}/convert_lora_to_gguf.py" \
    "${ADAPTER_DIR}" \
    --base "${TMP_BASE_DIR}" \
    --outfile "${OUTPUT_GGUF}"

  cat > "${MODELFILE_PATH}" <<EOF
FROM ${OLLAMA_BASE_MODEL}

ADAPTER /workspace/deploy/gguf_adapters/${ADAPTER_NAME}-lora.gguf

PARAMETER temperature 0.2
EOF

  echo "Generated ${MODELFILE_PATH}"
}

if [ "${1:-}" != "" ]; then
  process_adapter "$1"
  exit 0
fi

FOUND=0
for dir in "${ADAPTERS_ROOT}"/*; do
  [ -d "${dir}" ] || continue
  FOUND=1
  process_adapter "$(basename "${dir}")"
done

if [ "${FOUND}" -eq 0 ]; then
  echo "No adapter directories found in ${ADAPTERS_ROOT}" >&2
  exit 1
fi

echo "All adapters converted."
