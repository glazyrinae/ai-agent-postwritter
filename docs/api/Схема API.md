# Схема API

## Low-level endpoints

- `GET /` - мета-информация о сервисе и доступных агентах.
- `GET /health` - базовый healthcheck.
- `GET /models` - список моделей и LoRA alias из `vLLM`.
- `POST /pipeline` - LangChain pipeline поверх нескольких agent aliases.

Ответ `POST /pipeline`:
- `pipeline` - список использованных agent aliases
- `result` - итоговый текст последнего шага pipeline

Для всех endpoints, кроме `GET /health`, требуется заголовок:

```text
Authorization: Bearer <API_BEARER_TOKEN>
```

## Article endpoints

### `POST /articles/outline`

Назначение: сгенерировать outline статьи в markdown и сразу распарсить его в структурированный список разделов.

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

Назначение: синхронно сгенерировать полную статью для IT-блога по теме.

Вход:
- `topic`
- `outline_markdown` опционально
- `target_audience`
- `style`
- `desired_sections_count`
- `chapter_max_tokens`
- `context_mode`
- `include_code_examples`

Выход:
- `title`
- `outline_markdown`
- `sections[{title,description,content,summary}]`
- `article_markdown`

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
- `CONFIGURATION_ERROR`
- `INTERNAL_ERROR`
