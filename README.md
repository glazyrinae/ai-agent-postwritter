# Multi-Agent System with Ollama and vLLM

Docker-проект для запуска набора агентов через `FastAPI` и `LangChain` с двумя backend-режимами:

- `Ollama` как основной CPU-friendly runtime по умолчанию
- `vLLM` как ручной сервис для отдельных запусков и экспериментов

## Что есть в проекте

- `ollama-server` как основной OpenAI-compatible backend по умолчанию.
- `vllm-server` для ручного запуска через compose profile `manual`.
- `agent-api` на FastAPI в структуре `src/app`, `src/features`, `src/integrations`.
- low-level endpoints для LangChain pipeline, списка моделей и healthcheck.
- article endpoints для генерации outline и полной статьи.
- orchestration pipeline и article flow построены через `LangChain`, а backend выбирается на Docker/env уровне без изменения Python-кода.
- `model-downloader` для ручной загрузки модели из Hugging Face.
- `src/integrations/ollama_server/` для Ollama bootstrap-скриптов, локального GGUF fallback и shell workflow.
- `llama-converter` для контейнерной конверсии PEFT LoRA -> GGUF-adapter под Ollama.
- документация в `docs/`, проектовый контекст в `ai_context/`, тесты в `tests/`.

## Подготовка окружения

```bash
cp .env.example .env
```

Минимум в `.env` нужно проверить и при необходимости заполнить:

- `API_BEARER_TOKEN` - токен для доступа к защищенным API endpoints.
- `HF_TOKEN` - нужен только если модель недоступна анонимно.
- `UID`, `GID` - при необходимости смены пользователя контейнеров.
- `LLM_BASE_URL` - OpenAI-compatible backend для `agent-api`. По умолчанию указывает на `ollama-server`.
- `LLM_DEFAULT_MODEL` - имя модели для текущего backend. По умолчанию `cotype-nano-4bit`.
- `OLLAMA_HOST_DIR`, `OLLAMA_MODEL_NAME`, `OLLAMA_PUBLISHED_PORT` - параметры Ollama runtime.
- `OLLAMA_BASE_MODEL` - базовая Ollama-модель, поверх которой регистрируются конвертированные LoRA-модели.
- `LLAMA_CPP_REF` - версия `llama.cpp` для контейнера-конвертера.
- `VLLM_DTYPE` - для CPU рекомендуется `bfloat16`.
- `VLLM_CPU_KVCACHE_SPACE`, `VLLM_CPU_NUM_OF_RESERVED_CPU` - базовые параметры CPU backend `vLLM`.
- `VLLM_MAX_MODEL_LEN`, `VLLM_MAX_NUM_SEQS` - главные ограничители памяти на CPU. Если `vllm-server` падает на старте, уменьшайте сначала их.

Ключевые каталоги, которые использует compose:

- `deploy/models/` - базовая Hugging Face модель для `model-downloader` и ручного `vLLM` (сейчас по умолчанию `MTSAIR/Cotype-Nano-4bit`), а также storage для Ollama в `deploy/models/ollama/`.
- `deploy/lora_adapters/` - LoRA-адаптеры.
- `deploy/gguf_adapters/` - GGUF-адаптеры, сконвертированные из PEFT LoRA.
- `deploy/modelfiles/` - базовый fallback `Modelfile` и временные `Modelfile` для регистрации Ollama-моделей.

## Проверка конфигурации

Перед первым запуском:

```bash
docker compose config
```

На этом шаге стоит убедиться, что:

- `ollama-server` использует `deploy/models/ollama/`.
- `agent-api` получает `LLM_BASE_URL` и `LLM_DEFAULT_MODEL`.
- `agent-api` получает `API_BEARER_TOKEN`.
- `llama-converter` при необходимости может быть собран через profile `tools`.
- сервисы запускаются от `UID:GID`.

## Запуск сервисов

По умолчанию запуск идет через `Ollama`:

```bash
docker compose up -d ollama-server ollama-init agent-api
```

Ручной запуск `vLLM` и загрузчика:

```bash
docker compose --profile manual up -d model-downloader vllm-server
```

Полезные логи:

```bash
docker compose logs -f model-downloader
docker compose logs -f vllm-server
docker compose logs -f ollama-server
docker compose logs -f ollama-init
docker compose logs -f agent-api
```

Важно:

- `model-downloader` и `vllm-server` не стартуют по умолчанию.
- `Ollama` использует registry pull по умолчанию для базовой модели.
- PEFT LoRA не конвертируются локально на хосте: для этого есть отдельный контейнер `llama-converter`.

## Конвертация LoRA для Ollama

Контейнерный workflow для всех адаптеров:

```bash
docker compose --profile tools build llama-converter
src/integrations/ollama_server/scripts/build_ollama_lora_model.sh
```

Для одного адаптера:

```bash
docker compose --profile tools build llama-converter
src/integrations/ollama_server/scripts/build_ollama_lora_model.sh writer
```

Что делает эта команда:

- запускает `llama-converter` контейнер
- проходит по `deploy/lora_adapters/`
- конвертирует PEFT LoRA в `GGUF`-адаптеры
- сохраняет их в `deploy/gguf_adapters/`
- пишет временные `Modelfile` в `deploy/modelfiles/`
- удаляет старую Ollama-модель с тем же именем
- заново регистрирует новую модель в `ollama-server`

Формат имен новых моделей:

- `hodza_cotype-nano-1.5-unofficial_latest_writer`
- `hodza_cotype-nano-1.5-unofficial_latest_summarizer`
- `hodza_cotype-nano-1.5-unofficial_latest_editor`

Важно:

- базовая Ollama-модель и зарегистрированные производные модели хранятся в `deploy/models/ollama/`
- `.gguf` в `deploy/gguf_adapters/` — это адаптеры, а не полные merged-модели

## Быстрая проверка API

`GET /health` публичный. Остальные основные endpoints требуют Bearer token.

```bash
curl http://localhost:8080/health
curl http://localhost:8080/
curl -H "Authorization: Bearer $API_BEARER_TOKEN" http://localhost:8080/
curl -H "Authorization: Bearer $API_BEARER_TOKEN" http://localhost:8080/models
curl -H "Authorization: Bearer $API_BEARER_TOKEN" http://localhost:8080/docs
```

Ожидаемое поведение:

- `GET /health` должен отвечать `200`.
- `GET /` без токена должен отвечать `401`.
- `GET /` и `GET /models` с токеном должны отвечать `200`.

## Тестирование article feature

Сначала лучше проверить `outline`, а уже потом полную генерацию статьи.

Проверка `POST /articles/outline`:

```bash
curl -X POST http://localhost:8080/articles/outline \
  -H "Authorization: Bearer $API_BEARER_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "topic": "Как Kubernetes упрощает деплой Python-сервисов",
    "target_audience": "backend engineers",
    "style": "практический технический блог",
    "desired_sections_count": 3,
    "include_code_examples": true
  }'
```

Проверка `POST /articles/generate`:

```bash
curl -X POST http://localhost:8080/articles/generate \
  -H "Authorization: Bearer $API_BEARER_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "topic": "Как Kubernetes упрощает деплой Python-сервисов",
    "target_audience": "backend engineers",
    "style": "практический технический блог",
    "desired_sections_count": 3,
    "chapter_max_tokens": 1200,
    "context_mode": "summaries",
    "include_code_examples": true
  }'
```

Для первой диагностики лучше держать:

- `desired_sections_count: 3`
- `chapter_max_tokens: 1200`

Так быстрее найти инфраструктурные ошибки и не тратить много времени на длинную генерацию.

## Как тестировать сервис

### 1. Статические проверки

```bash
python3 -m compileall src tests
docker compose config
```

### 2. Быстрые автотесты

```bash
pytest tests/unit
pytest tests/integration
```

Эти тесты не требуют живой модели. Они проверяют orchestration, API и обработку ошибок через stubbed client.

### 3. Ручные smoke-тесты на живом стеке

```bash
curl http://localhost:8080/health

curl http://localhost:8080/

curl -H "Authorization: Bearer $API_BEARER_TOKEN" \
  http://localhost:8080/models

curl -X POST http://localhost:8080/articles/outline \
  -H "Authorization: Bearer $API_BEARER_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "topic": "Как Kubernetes упрощает деплой Python-сервисов",
    "desired_sections_count": 3,
    "include_code_examples": true
  }'

curl -X POST http://localhost:8080/articles/generate \
  -H "Authorization: Bearer $API_BEARER_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "topic": "Как Kubernetes упрощает деплой Python-сервисов",
    "desired_sections_count": 3,
    "chapter_max_tokens": 1200,
    "context_mode": "summaries",
    "include_code_examples": true
  }'
```

## Основные API endpoints

Публичный endpoint:

- `GET /health`

Защищенные endpoints:

- `GET /`
- `GET /models`
- `POST /pipeline`
- `POST /articles/outline`
- `POST /articles/generate`

LangChain pipeline поверх agent aliases:

```bash
curl -X POST http://localhost:8080/pipeline \
  -H "Authorization: Bearer $API_BEARER_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "initial_prompt": "Черновик статьи про Kubernetes",
    "pipeline": ["summarizer", "writer"]
  }'
```

Ответ содержит:

- `pipeline` - список использованных agent aliases
- `result` - итоговый текст последнего шага pipeline

Сначала стоит прогнать `POST /articles/outline`, чтобы проверить, что модель стабильно выдает структуру статьи.

Генерация outline статьи:

```bash
curl -X POST http://localhost:8080/articles/outline \
  -H "Authorization: Bearer $API_BEARER_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "topic": "Как Kubernetes упрощает деплой Python-сервисов",
    "target_audience": "backend engineers",
    "style": "практический технический блог",
    "desired_sections_count": 5,
    "include_code_examples": true
  }'
```

После этого можно переходить к `POST /articles/generate`.

Генерация полной статьи:

```bash
curl -X POST http://localhost:8080/articles/generate \
  -H "Authorization: Bearer $API_BEARER_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "topic": "Как Kubernetes упрощает деплой Python-сервисов",
    "target_audience": "backend engineers",
    "style": "практический технический блог",
    "desired_sections_count": 3,
    "chapter_max_tokens": 1200,
    "context_mode": "summaries"
  }'
```

## Структура

- `src/app/` - entrypoint, settings, DI и регистрация роутеров.
- `src/core/` - ошибки и логирование.
- `src/features/agents/` - low-level agent API.
- `src/features/articles/` - синхронная генерация длинных IT-статей.
- `src/integrations/vllm_server/` - клиент к OpenAI-compatible backend API.
- `src/integrations/langchain/` - LangChain orchestration поверх backend-модели.
- `deploy/` - Dockerfiles, загрузка HF-модели и ручный `vLLM`.
- `src/integrations/ollama_server/` - Ollama model registration, контейнерная конверсия LoRA и GGUF-артефакты.
- `docs/` - архитектура, API и требования.
- `ai_context/` - журнал и ключевые решения по проекту.
- `tests/` - unit и integration тесты.

## Авторизация

- Все основные API endpoints защищены `Authorization: Bearer <token>`.
- Токен задается через `API_BEARER_TOKEN` в `.env`.
- `GET /health` остается без авторизации для healthcheck.

## Если что-то не работает

- `401` на `/`, `/models` или `/articles/*` - проверьте `API_BEARER_TOKEN` и заголовок `Authorization: Bearer ...`.
- `model-downloader` падает - проверьте `HF_TOKEN` и доступность модели `MODEL_ID`.
- `vllm-server` не стартует - проверьте `MODEL_DIR`, наличие файлов в `deploy/models/`, поддержку CPU backend и значения `VLLM_DTYPE`, `VLLM_CPU_KVCACHE_SPACE`, `VLLM_CPU_NUM_OF_RESERVED_CPU`, `VLLM_MAX_MODEL_LEN`, `VLLM_MAX_NUM_SEQS`.
- `build_ollama_lora_model.sh` падает - сначала соберите `llama-converter` через `docker compose --profile tools build llama-converter`.
- `/articles/generate` отвечает ошибкой - сначала проверьте `/models` и `POST /articles/outline`.
- `docker compose config` показывает неожиданные пути - проверьте `MODEL_HOST_DIR` и `LORA_HOST_DIR` в `.env`.

## Требования

- Docker Engine и Docker Compose.
- Для default-path на Ollama GPU не требуется.
- Для ручного `vLLM` на CPU это все еще экспериментальный режим.

## Лицензия

MIT
