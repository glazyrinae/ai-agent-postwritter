from fastapi import APIRouter, Depends

from src.app.container import AppContainer, get_container
from src.features.articles.schemas import (
    ArticleGenerateRequest,
    ArticleGenerateResponse,
    ArticleRunStatusResponse,
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
        "понимает тему и держит структуру. Внутренне сервис просит у модели структурированный "
        "outline и сам собирает из него markdown-outline и список разделов."
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
        "Полный sync article workflow: сервис принимает только тему, сам строит outline, "
        "последовательно генерирует главы, summaries для контекста, заключение, финальный "
        "proofreading pass и сохраняет прогресс в PostgreSQL."
    ),
    response_description="Полностью собранная статья, все разделы, итоговый markdown и run_id.",
)
async def generate_article(
    request: ArticleGenerateRequest,
    container: AppContainer = Depends(get_container),
):
    return container.article_service.generate_article(request)


@router.get(
    "/runs/{run_id}",
    response_model=ArticleRunStatusResponse,
    summary="Получить статус сохраненного запуска генерации статьи",
    response_description="Статус, последний шаг, outline и уже сохраненные разделы article run.",
)
async def get_article_run_status(
    run_id: str,
    container: AppContainer = Depends(get_container),
):
    return container.article_service.get_run_status(run_id)


@router.get(
    "/runs/{run_id}/result",
    response_model=ArticleGenerateResponse,
    summary="Получить сохраненный итог статьи по run_id",
    response_description="Полностью собранная статья, если сохраненный запуск уже завершен.",
)
async def get_article_run_result(
    run_id: str,
    container: AppContainer = Depends(get_container),
):
    return container.article_service.get_run_result(run_id)
