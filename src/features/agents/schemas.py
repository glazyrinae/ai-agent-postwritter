from pydantic import BaseModel, Field


class MultiAgentRequest(BaseModel):
    initial_prompt: str = Field(
        description="Исходный текст или запрос, который будет последовательно обработан агентами pipeline.",
        examples=["Сделай черновик статьи про Kubernetes для backend-разработчиков."],
    )
    pipeline: list[str] = Field(
        description=(
            "Список агентных alias в порядке выполнения. "
            "Каждый следующий агент получает результат предыдущего шага."
        ),
        examples=[["summarizer", "writer"]],
    )


class DebugPromptRequest(BaseModel):
    model: str | None = Field(
        default=None,
        description="Имя backend-модели для прямого debug-вызова. Если не задано, используется базовая модель из настроек.",
        examples=["hodza/cotype-nano-1.5-unofficial"],
    )
    prompt: str = Field(
        description="Текст запроса, который будет отправлен в backend-модель напрямую.",
        examples=["Напиши короткий технический абзац про трансформеры."],
    )


class DebugPromptResponse(BaseModel):
    model: str = Field(description="Модель, которая фактически была использована для debug-вызова.")
    result: str = Field(description="Текстовый ответ backend-модели.")
