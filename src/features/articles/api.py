from fastapi import APIRouter, Depends

from src.app.container import AppContainer, get_container
from src.features.articles.schemas import (
    ArticleGenerateRequest,
    ArticleGenerateResponse,
    OutlineRequest,
    OutlineResponse,
)

router = APIRouter(prefix="/articles", tags=["articles"])


@router.post(
    "/outline",
    response_model=OutlineResponse,
    summary="Сгенерировать outline статьи",
    description=(
        "Создает структуру будущей статьи на основе темы, аудитории и желаемого стиля. "
        "Сначала вызывайте этот endpoint, если хотите проверить, насколько хорошо модель "
        "понимает тему и держит структуру. В ответе возвращаются и сырой markdown-outline, "
        "и уже распарсенные разделы."
    ),
    response_description="Заголовок статьи, markdown-outline и распарсенные разделы.",
)
async def generate_outline(
    request: OutlineRequest,
    container: AppContainer = Depends(get_container),
):
    return container.article_service.generate_outline(request)


@router.post(
    "/generate",
    response_model=ArticleGenerateResponse,
    summary="Сгенерировать полную статью",
    description=(
        "Полный article workflow: при необходимости сервис сначала строит outline, затем "
        "последовательно генерирует главы, summaries для контекста следующих глав и финальное "
        "заключение. Используйте этот endpoint, когда нужен уже готовый markdown-текст статьи, "
        "а не только ее структура."
    ),
    response_description="Полностью собранная статья, все разделы и итоговый markdown.",
)
async def generate_article(
    request: ArticleGenerateRequest,
    container: AppContainer = Depends(get_container),
):
    return container.article_service.generate_article(request)
