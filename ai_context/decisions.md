# Ключевые решения

## Архитектура

- Runtime-код API хранится в `src/`.
- Архитектура разделена на `app`, `core`, `features`, `integrations`.
- Для текущей версии не вводятся БД, очереди и фоновые job'ы.
- Все основные API endpoints защищены Bearer token авторизацией; `GET /health` остается публичным.
- Контейнеры запускаются с `UID/GID` из env, по умолчанию `1000:1000`.

## Генерация статей

- Генерация длинной статьи реализована синхронно через HTTP.
- Для article flow orchestration используется LangChain.
- Для pipeline-слоя orchestration используется LangChain.
- Прямой публичный endpoint `/agent/{agent_name}` удален; внешняя orchestration идет через `/pipeline` и article workflows.
- Для outline, sections и conclusion используется агент `writer`.
- Для summary-контекста используется агент `summarizer`.
- Контекст следующих глав формируется на основе summary предыдущих разделов, а не полного текста.
- Outline и заключение генерируются отдельными шагами.

## Документация

- Каноничные проектовые правила фиксируются в `AGENTS.md`.
- Архитектурные и API-контракты дублируются в `docs/`.

## Ollama артефакты

- GGUF-адаптеры для Ollama хранятся в `deploy/gguf_adapters/`, а не в `src/`.
- Базовый fallback `Modelfile` и сгенерированные `Modelfile` для перерегистрации Ollama-моделей хранятся в `deploy/modelfiles/`.
