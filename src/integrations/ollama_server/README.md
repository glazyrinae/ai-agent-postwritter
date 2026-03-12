# Ollama Backend

Этот каталог содержит все, что относится к CPU-friendly backend на базе `Ollama`.

## Что здесь лежит

- `deploy/modelfiles/Modelfile` - описание локальной GGUF-модели для `ollama create`.
- `ollama-entrypoint.sh` - bootstrap-скрипт, который ждет старта Ollama и регистрирует модель.
- `models/` - место для локального GGUF-файла, если вы захотите использовать локальную модель вместо registry pull.
- storage Ollama хранится в `deploy/models/ollama/`.
- `scripts/convert_to_gguf.sh` - вспомогательный шаблон для конверсии HF-модели в GGUF.
- `scripts/build_ollama_lora_model.sh` - контейнерный wrapper: конвертация PEFT LoRA в GGUF-adapter и регистрация новой Ollama-модели.
- `scripts/build_ollama_lora_model_inner.sh` - внутренняя конвертация, которую запускает `llama-converter`.

## Режим по умолчанию

По умолчанию `ollama-init` делает:

```bash
ollama pull hodza/cotype-nano-1.5-unofficial
```

Это позволяет поднять Ollama без локального GGUF-файла.

Базовый `deploy/modelfiles/Modelfile` и `models/` остаются в проекте как запасной путь для будущей GGUF-модели.

## Быстрые команды

Поднять Ollama и API:

```bash
docker compose up -d ollama-server ollama-init agent-api
```

Поднять ручной `vLLM`:

```bash
docker compose --profile manual up -d model-downloader vllm-server
```

## Конвертация LoRA для Ollama

Для текущих адаптеров из `deploy/lora_adapters/` есть пакетный workflow:

```bash
src/integrations/ollama_server/scripts/build_ollama_lora_model.sh
```

Что делает скрипт:

- проходит по всем папкам в `deploy/lora_adapters/`
- запускает `llama-converter` контейнер, а не локальный Python
- создает временную `config-only` базу без AWQ metadata
- запускает `llama.cpp/convert_lora_to_gguf.py`
- сохраняет адаптеры в `deploy/gguf_adapters/`
- пишет временные `Modelfile` в `deploy/modelfiles/`
- удаляет старую Ollama-модель с тем же именем, если она уже существует
- заново регистрирует новую модель в контейнере `ollama-server` через `ollama create`

Имя модели формируется так:

```text
<base-model-name>_<adapter-folder-name>
```

Для текущей базы это будут модели вида:

- `hodza_cotype-nano-1.5-unofficial_latest_writer`
- `hodza_cotype-nano-1.5-unofficial_latest_summarizer`
- `hodza_cotype-nano-1.5-unofficial_latest_editor`

Если нужен только один адаптер:

```bash
src/integrations/ollama_server/scripts/build_ollama_lora_model.sh writer
```
