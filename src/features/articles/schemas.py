from typing import Literal

from pydantic import BaseModel, Field


class OutlineRequest(BaseModel):
    topic: str = Field(
        description="Тема будущей статьи. На ее основе модель строит заголовок и структуру outline.",
        examples=["Как Kubernetes упрощает деплой Python-сервисов"],
    )
    target_audience: str = Field(
        default="IT engineers",
        description="Целевая аудитория статьи. Влияет на глубину, терминологию и подачу материала.",
        examples=["backend engineers", "DevOps engineers"],
    )
    style: str = Field(
        default="практический технический блог",
        description="Желаемый стиль изложения: насколько текст должен быть практическим, академичным или прикладным.",
        examples=["практический технический блог"],
    )
    desired_sections_count: int = Field(
        default=5,
        ge=3,
        le=8,
        description="Сколько основных разделов должно быть в outline. Заключение в это число не входит.",
    )
    include_code_examples: bool = Field(
        default=True,
        description="Нужно ли ориентировать outline и статью на наличие примеров кода, CLI-команд и конфигураций.",
    )


class ParsedOutlineSection(BaseModel):
    index: int = Field(description="Порядковый номер раздела в outline.")
    title: str = Field(description="Название раздела.")
    description: str = Field(description="Краткое описание того, что должно быть раскрыто в разделе.")


class OutlineResponse(BaseModel):
    title: str = Field(description="Итоговый заголовок статьи.")
    outline_markdown: str = Field(
        description="Сырой markdown-outline, который вернула модель. Его можно переиспользовать в следующем запросе."
    )
    sections: list[ParsedOutlineSection] = Field(
        description="Структурированное представление outline после парсинга."
    )


class ArticleGenerateRequest(BaseModel):
    topic: str = Field(
        description="Основная тема статьи. Используется и для генерации outline, и для генерации самих глав.",
        examples=["Как Kubernetes упрощает деплой Python-сервисов"],
    )
    outline_markdown: str | None = Field(
        default=None,
        description=(
            "Готовый outline статьи в markdown. "
            "Если не передан, сервис сначала сам вызовет этап генерации outline."
        ),
    )
    target_audience: str = Field(
        default="IT engineers",
        description="Целевая аудитория статьи. Влияет на глубину объяснений и терминологию.",
    )
    style: str = Field(
        default="практический технический блог",
        description="Желаемый стиль изложения для всех глав и заключения.",
    )
    desired_sections_count: int = Field(
        default=5,
        ge=3,
        le=8,
        description="Количество разделов, если outline будет генерироваться автоматически.",
    )
    chapter_max_tokens: int | None = Field(
        default=None,
        ge=500,
        le=4000,
        description="Максимальное число токенов на одну главу. Если не задано, используется серверное значение по умолчанию.",
    )
    context_mode: Literal["summaries"] = Field(
        default="summaries",
        description="Способ передачи контекста между главами. Сейчас поддерживается только summaries.",
    )
    include_code_examples: bool = Field(
        default=True,
        description="Нужно ли просить модель включать код, CLI-команды или конфигурации там, где это уместно.",
    )


class ArticleSectionResult(BaseModel):
    title: str = Field(description="Название сгенерированного раздела.")
    description: str = Field(description="Описание раздела из outline.")
    content: str = Field(description="Полный текст сгенерированной главы.")
    summary: str = Field(description="Краткое summary главы, использованное как контекст для следующих разделов.")


class ArticleGenerateResponse(BaseModel):
    title: str = Field(description="Итоговый заголовок статьи.")
    outline_markdown: str = Field(description="Outline статьи в markdown.")
    sections: list[ArticleSectionResult] = Field(description="Все сгенерированные разделы статьи.")
    article_markdown: str = Field(description="Полностью собранная статья в markdown, включая заключение.")
