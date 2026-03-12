from dataclasses import dataclass

from fastapi import Request

from src.app.settings import Settings
from src.features.agents.service import AgentService
from src.features.articles.repository import ArticleRunRepository
from src.features.articles.service import ArticleService
from src.integrations.vllm_server import VLLMClient


@dataclass
class AppContainer:
    settings: Settings
    vllm_client: VLLMClient
    article_run_repository: ArticleRunRepository
    agent_service: AgentService
    article_service: ArticleService


def build_container(settings: Settings) -> AppContainer:
    vllm_client = VLLMClient(base_url=settings.vllm_url, default_model=settings.default_model)
    article_run_repository = ArticleRunRepository(database_url=settings.database_url)
    article_run_repository.ensure_schema()
    agent_service = AgentService(settings=settings, vllm_client=vllm_client)
    article_service = ArticleService(
        settings=settings,
        vllm_client=vllm_client,
        repository=article_run_repository,
    )
    return AppContainer(
        settings=settings,
        vllm_client=vllm_client,
        article_run_repository=article_run_repository,
        agent_service=agent_service,
        article_service=article_service,
    )


def get_container(request: Request) -> AppContainer:
    return request.app.state.container
