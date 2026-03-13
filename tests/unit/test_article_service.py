from types import SimpleNamespace

from src.app.settings import Settings
from src.core.errors import ConfigurationError, EmptyModelResponseError
from src.features.articles.repository import ArticleRunRepository
from src.features.articles.schemas import ArticleSectionResult
from src.features.articles.service import ArticleService


class FakeLLMClient:
    def __init__(self, responses: list[str]):
        self.responses = responses
        self.calls = []

    def generate(self, **kwargs):
        self.calls.append(kwargs)
        return self.responses.pop(0)


class FakeRepository:
    def __getattr__(self, name):
        def _noop(*args, **kwargs):
            return None

        return _noop


def test_article_service_requires_writer_alias():
    settings = Settings()
    settings.available_agents = {"editor": "editor"}
    try:
        ArticleService(settings=settings, llm_client=FakeLLMClient([]), repository=FakeRepository())
    except ConfigurationError as exc:
        assert exc.code == "CONFIGURATION_ERROR"
    else:
        raise AssertionError("ConfigurationError was not raised")


def test_compile_article_builds_markdown_document():
    service = ArticleService(settings=Settings(), llm_client=FakeLLMClient(["ok"]), repository=FakeRepository())
    article = service.compile_article(
        title="Kubernetes",
        sections=[
            ArticleSectionResult(
                title="Раздел 1",
                description="desc",
                content="Подробное содержание раздела.",
                summary="summary",
            )
        ],
        conclusion="Финальный вывод.",
    )

    assert article.startswith("# Kubernetes")
    assert "## Раздел 1" in article
    assert "## Заключение" in article


def test_generate_section_raises_when_content_is_too_short():
    settings = Settings()
    settings.article_min_section_chars = 50
    service = ArticleService(settings=settings, llm_client=FakeLLMClient(["слишком коротко"]), repository=FakeRepository())

    try:
        service.generate_section(
            topic="Kubernetes",
            outline_markdown="# Title\n1. Раздел :: Описание",
            section=SimpleNamespace(title="Раздел", description="Описание"),
            target_audience="engineers",
            style="технический блог",
            previous_summaries=[],
            include_code_examples=True,
            chapter_max_tokens=900,
        )
    except EmptyModelResponseError as exc:
        assert exc.code == "EMPTY_MODEL_RESPONSE"
    else:
        raise AssertionError("EmptyModelResponseError was not raised")


def test_summaries_use_summarizer_agent_when_available():
    fake_client = FakeLLMClient(["Краткое summary раздела."])
    service = ArticleService(settings=Settings(), llm_client=fake_client, repository=FakeRepository())

    summary = service.summarize_section_for_context(
        section_title="Раздел",
        section_text="Очень длинный и содержательный текст раздела " * 20,
    )

    assert summary == "Краткое summary раздела."
    assert fake_client.calls[0]["model"] == "summarizer"
