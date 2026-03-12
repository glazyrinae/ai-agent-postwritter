# Схема API

## Low-level endpoints

- `GET /` - мета-информация о сервисе и доступных агентах.
- `GET /health` - базовый healthcheck.
- `GET /models` - список моделей и LoRA alias из `vLLM`.
- `POST /pipeline` - LangChain pipeline поверх нескольких agent aliases.
- `POST /debug/prompt` - прямой debug-вызов backend-модели.

Ответ `POST /pipeline`:
- `pipeline` - список использованных agent aliases
- `result` - итоговый текст последнего шага pipeline

### `POST /debug/prompt`

Назначение: отправить произвольный prompt напрямую в backend-модель без LangChain pipeline.

Вход:
- `prompt`
- `model` опционально

Выход:
- `model`
- `result`

Для всех endpoints, кроме `GET /health`, требуется заголовок:

```text
Authorization: Bearer <API_BEARER_TOKEN>
```

## Article endpoints

### `POST /articles/outline`

Назначение: сгенерировать структурированный outline статьи и вернуть его как markdown-outline и как список разделов.

Вход:
- `topic`
- `target_audience`
- `style`
- `desired_sections_count`
- `include_code_examples`

Выход:
- `title`
- `outline_markdown`
- `sections[{index,title,description}]`

### `POST /articles/generate`

Назначение: синхронно сгенерировать полную статью для IT-блога только по теме. Все остальные параметры сервис берет из серверных настроек.

Вход:
- `topic`

Выход:
- `run_id`
- `status`
- `title`
- `outline_markdown`
- `sections[{title,description,content,summary}]`
- `article_markdown`

### `GET /articles/runs/{run_id}`

Назначение: получить статус сохраненного article run и уже сохраненные части статьи.

Выход:
- `run_id`
- `status`
- `topic`
- `title`
- `current_step`
- `last_error`
- `outline_markdown`
- `sections[{index,title,description,status,content,summary}]`

### `GET /articles/runs/{run_id}/result`

Назначение: получить сохраненный итог статьи по `run_id`, если синхронная генерация уже завершилась.

## Формат ошибок

Все прикладные ошибки возвращаются как:

```json
{
  "error": {
    "code": "OUTLINE_PARSE_FAILED",
    "message": "Could not parse outline into sections.",
    "details": {}
  }
}
```

Используемые коды:
- `OUTLINE_PARSE_FAILED`
- `UPSTREAM_UNAVAILABLE`
- `EMPTY_MODEL_RESPONSE`
- `RESOURCE_NOT_FOUND`
- `INVALID_STATE`
- `STORAGE_UNAVAILABLE`
- `CONFIGURATION_ERROR`
- `INTERNAL_ERROR`
