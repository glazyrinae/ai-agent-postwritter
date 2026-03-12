from fastapi import Depends, FastAPI

from src.core.auth import require_bearer_token
from src.features.agents.api import public_router as public_agent_router
from src.features.agents.api import router as agent_router
from src.features.articles.api import router as article_router


def register_routers(app: FastAPI) -> None:
    app.include_router(public_agent_router)
    app.include_router(agent_router, dependencies=[Depends(require_bearer_token)])
    app.include_router(article_router, dependencies=[Depends(require_bearer_token)])
