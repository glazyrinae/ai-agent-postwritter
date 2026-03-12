from dataclasses import dataclass

from fastapi import Request

from src.app.settings import Settings
from src.features.agents.service import AgentService
from src.features.articles.service import ArticleService
from src.integrations.vllm_server import VLLMClient


@dataclass
class AppContainer:
    settings: Settings
    vllm_client: VLLMClient
    agent_service: AgentService
    article_service: ArticleService


def build_container(settings: Settings) -> AppContainer:
    vllm_client = VLLMClient(base_url=settings.vllm_url, default_model=settings.default_model)
    agent_service = AgentService(settings=settings, vllm_client=vllm_client)
    article_service = ArticleService(settings=settings, vllm_client=vllm_client)
    return AppContainer(
        settings=settings,
        vllm_client=vllm_client,
        agent_service=agent_service,
        article_service=article_service,
    )


def get_container(request: Request) -> AppContainer:
    return request.app.state.container
