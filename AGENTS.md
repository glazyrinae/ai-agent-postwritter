# AGENTS.md

## Назначение проекта

Этот репозиторий содержит Docker-first мульти-агентную систему на `vLLM + LoRA + FastAPI`.
Текущая целевая архитектура построена вокруг `src/app`, `src/core`, `src/features`, `src/integrations` и отдельной feature генерации длинных статей для IT-блога.

## Где что находится

- `src/app/` - composition root, lifecycle, settings, DI и подключение роутеров.
- `src/core/errors/` - единый формат ошибок API и exception mapping.
- `src/core/logging/` - конфигурация логирования.
- `src/core/auth.py` - Bearer token авторизация для защищенных API endpoints.
- `src/features/agents/` - low-level API для `/pipeline`, `/models`, `/health`.
- `src/features/articles/` - outline, поэтапная генерация глав, summary-контекст и сборка итоговой статьи.
- `src/integrations/vllm_server/` - клиент OpenAI-compatible API для vLLM.
- `src/integrations/langchain/` - LangChain orchestration и вызов agent aliases для pipeline и article flow.
- `deploy/` - Dockerfiles, скрипт загрузки, `deploy/models/` для базовой модели и `deploy/lora_adapters/` для LoRA.
- `docs/` - каноничная документация по архитектуре, API и сценариям.
- `ai_context/` - краткий журнал и ключевые решения по проекту.
- `tests/` - unit и integration тесты.

## Обязательные правила изменений

- Новую прикладную логику добавляй в `src/features/`, а не в `src/app/` или `src/integrations/`.
- Внешние API-клиенты держи в `src/integrations/`, без доменной orchestration внутри них.
- Весь pipeline-слой и article flow должны идти через LangChain abstraction, а не через ручные прямые вызовы `vllm_client.chat()` из feature-кода.
- Если меняешь env-конфиг, синхронно обновляй `src/app/settings.py`, `.env.example`, `README.md` и релевантные документы в `docs/`.
- Если меняешь авторизацию, синхронно обновляй код dependency, README, OpenAPI и integration-тесты.
- Если меняешь публичные HTTP-контракты, синхронно обновляй код роутеров, `docs/api/openapi.yaml`, `docs/api/Схема API.md` и примеры в `README.md`.
- Если добавляешь нового агента, обновляй одновременно `deploy/lora_adapters/`, настройки `available_agents`, LangChain orchestration и документацию.
- Для article feature держи orchestration в `src/features/articles/service.py`, а шаблоны prompt’ов в `src/features/articles/prompts.py`.
- Не коммить реальные веса моделей, Hugging Face токены, содержимое `deploy/models/`, содержимое `deploy/lora_adapters/` с обученными артефактами и локальные `.env`.
- Контейнеры должны по умолчанию запускаться с `UID/GID` из env; если меняешь compose, не ломай этот контракт.

## Документация и контекст

- Ключевые решения фиксируй в `ai_context/decisions.md`.
- Краткие технические изменения фиксируй в `ai_context/ai.log`.
- Если решение устарело, переноси его в `ai_context/decisions.archive.md`, а не затирай бесследно.
- Каноничное описание архитектуры и API находится в `docs/`, не в README.

## Проверки после изменений

- Минимум: `python3 -m compileall src tests`.
- Для API: импорт приложения из `src.app.main`.
- Для Docker-конфига: `docker compose config`.
- Если менялось поведение HTTP API: прогон `pytest` или как минимум integration smoke-тесты.

## Стиль работы

- Документацию по проекту пиши на русском языке.
- Предпочитай простые явные слои и минимально достаточную абстракцию.
