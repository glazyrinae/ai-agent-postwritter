from fastapi import APIRouter, Depends, HTTPException

from src.app.container import AppContainer, get_container
from src.features.agents.schemas import DebugPromptRequest, DebugPromptResponse, MultiAgentRequest

public_router = APIRouter(tags=["agents"])
router = APIRouter(tags=["agents"])


@router.get(
    "/",
    summary="Информация о сервисе и доступных агентах",
    description=(
        "Возвращает базовую информацию о запущенном API: имя приложения, его версию и "
        "словарь доступных agent aliases. Этот endpoint полезен как быстрый sanity-check "
        "для защищенной части API и как источник актуального списка агентных ролей."
    ),
    response_description="Метаданные сервиса и доступные агентные alias.",
)
async def root(container: AppContainer = Depends(get_container)):
    return {
        "message": container.settings.app_name,
        "version": container.settings.app_version,
        "agents": container.settings.available_agents,
    }


@public_router.get(
    "/health",
    summary="Публичный healthcheck",
    description=(
        "Публичный endpoint для liveness/readiness-проверки. Не требует Bearer-токена. "
        "Показывает только то, что API-процесс жив и отвечает на HTTP-запросы."
    ),
    response_description="Простой статус здоровья сервиса.",
)
async def health():
    return {"status": "healthy", "vllm_connected": True}


@router.get(
    "/models",
    summary="Список моделей, доступных в backend",
    description=(
        "Запрашивает у upstream backend список доступных моделей. В зависимости от текущего "
        "runtime это могут быть модели Ollama, vLLM или другой OpenAI-compatible backend. "
        "Используйте этот endpoint, чтобы убедиться, что нужные `writer`, `summarizer`, "
        "`editor` или другие alias реально зарегистрированы."
    ),
    response_description="Список имен моделей, доступных в текущем backend.",
)
async def list_models(container: AppContainer = Depends(get_container)):
    return {"models": container.llm_client.list_models()}


@router.post(
    "/pipeline",
    summary="Запуск последовательного multi-agent pipeline",
    description=(
        "Принимает исходный текст и список agent aliases. Сервис прогоняет текст через них "
        "по очереди: результат каждого шага становится входом следующего. Это универсальный "
        "низкоуровневый endpoint для цепочек вроде `summarizer -> writer` или `writer -> editor`."
    ),
    response_description="Итоговый результат после прохождения всего pipeline.",
)
async def run_pipeline(
    request: MultiAgentRequest,
    container: AppContainer = Depends(get_container),
):
    try:
        final_response = container.agent_service.run_pipeline(
            pipeline=request.pipeline,
            initial_prompt=request.initial_prompt,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return {"pipeline": request.pipeline, "result": final_response}


@router.post(
    "/debug/prompt",
    response_model=DebugPromptResponse,
    summary="Прямой debug-вызов backend-модели",
    description=(
        "Принимает произвольный prompt и опциональное имя backend-модели. "
        "Если модель не передана, используется базовая модель из настроек. "
        "Этот endpoint ходит в backend напрямую, без LangChain pipeline и без article orchestration."
    ),
    response_description="Имя использованной модели и ее прямой текстовый ответ.",
)
async def debug_prompt(
    request: DebugPromptRequest,
    container: AppContainer = Depends(get_container),
):
    model, result = container.agent_service.debug_prompt(
        prompt=request.prompt,
        model=request.model,
    )
    return {"model": model, "result": result}
