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
