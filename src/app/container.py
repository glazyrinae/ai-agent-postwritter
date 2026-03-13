from dataclasses import dataclass

from fastapi import Request

from src.app.settings import Settings
from src.features.agents.service import AgentService
from src.features.articles.repository import ArticleRunRepository
from src.features.articles.service import ArticleService
from src.integrations.llm_server import LLMClient


@dataclass
class AppContainer:
    settings: Settings
    llm_client: LLMClient
    article_run_repository: ArticleRunRepository
    agent_service: AgentService
    article_service: ArticleService


def build_container(settings: Settings) -> AppContainer:
    llm_client = LLMClient(
        backend=settings.llm_backend,
        base_url=settings.llm_base_url,
        default_model=settings.default_model,
        request_timeout_seconds=settings.llm_request_timeout_seconds,
    )
    article_run_repository = ArticleRunRepository(database_url=settings.database_url)
    article_run_repository.ensure_schema()
    agent_service = AgentService(settings=settings, llm_client=llm_client)
    article_service = ArticleService(
        settings=settings,
        llm_client=llm_client,
        repository=article_run_repository,
    )
    return AppContainer(
        settings=settings,
        llm_client=llm_client,
        article_run_repository=article_run_repository,
        agent_service=agent_service,
        article_service=article_service,
    )


def get_container(request: Request) -> AppContainer:
    return request.app.state.container
