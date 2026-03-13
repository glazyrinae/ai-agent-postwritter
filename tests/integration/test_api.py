from types import SimpleNamespace

from fastapi.testclient import TestClient

from src.app.main import create_app

AUTH_HEADERS = {"Authorization": "Bearer change-me"}


class StubClient:
    def __init__(self, responses: list[str]):
        self.responses = responses

    def generate(self, **kwargs):
        return self.responses.pop(0)

    def stream(self, **kwargs):
        yield "chunk-1"
        yield "chunk-2"

    def list_models(self):
        return ["editor", "summarizer", "writer"]


def override_container(app, responses: list[str]):
    from src.app.container import build_container
    from src.app.settings import Settings

    container = build_container(Settings())
    container.llm_client = StubClient(responses)
    container.agent_service.llm_client = container.llm_client
    container.agent_service.orchestrator.client = container.llm_client
    container.article_service.llm_client = container.llm_client
    container.article_service.orchestrator.client = container.llm_client
    app.state.container = container


def test_outline_endpoint_returns_parsed_sections():
    app = create_app()
    with TestClient(app) as client:
        override_container(
            app,
            responses=[
                '{"title":"Kubernetes для backend-команд","sections":['
                '{"title":"Зачем нужен кластер","description":"Какие проблемы решает orchestration"},'
                '{"title":"Архитектура control plane","description":"Какие компоненты управляют кластером"},'
                '{"title":"Workloads","description":"Как запускать сервисы и jobs"}]}'
            ],
        )

        response = client.post(
            "/articles/outline",
            json={"topic": "Kubernetes", "desired_sections_count": 3},
            headers=AUTH_HEADERS,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["title"] == "Kubernetes для backend-команд"
        assert len(data["sections"]) == 3


def test_generate_article_endpoint_returns_article_markdown():
    app = create_app()
    with TestClient(app) as client:
        override_container(
            app,
            responses=[
                '{"title":"Kubernetes для backend-команд","sections":['
                '{"title":"Зачем нужен кластер","description":"Какие проблемы решает orchestration"},'
                '{"title":"Архитектура control plane","description":"Какие компоненты управляют кластером"},'
                '{"title":"Workloads","description":"Как запускать сервисы и jobs"}]}',
                "Первый раздел достаточно длинный и полезный. " * 10,
                "Summary первого раздела.",
                "Второй раздел достаточно длинный и полезный. " * 10,
                "Summary второго раздела.",
                "Третий раздел достаточно длинный и полезный. " * 10,
                "Summary третьего раздела.",
                "Итоговое заключение со следующими шагами.",
                "# Kubernetes для backend-команд\n\nИтоговая вычитанная статья.",
            ],
        )

        response = client.post(
            "/articles/generate",
            json={"topic": "Kubernetes"},
            headers=AUTH_HEADERS,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["title"] == "Kubernetes для backend-команд"
        assert len(data["sections"]) == 3
        assert "# Kubernetes для backend-команд" in data["article_markdown"]


def test_invalid_outline_returns_422():
    app = create_app()
    with TestClient(app) as client:
        override_container(app, responses=["Невалидный outline без структуры"])

        response = client.post(
            "/articles/outline",
            json={"topic": "Kubernetes"},
            headers=AUTH_HEADERS,
        )

        assert response.status_code == 422
        assert response.json()["error"]["code"] == "OUTLINE_PARSE_FAILED"


def test_direct_agent_endpoint_is_removed():
    app = create_app()
    with TestClient(app) as client:
        response = client.post(
            "/agent/writer",
            headers=AUTH_HEADERS,
        )

        assert response.status_code == 404


def test_pipeline_endpoint_returns_langchain_pipeline_result():
    app = create_app()
    with TestClient(app) as client:
        override_container(
            app,
            responses=[
                "Краткое summary входного текста.",
                "Финальная статья после writer.",
            ],
        )

        response = client.post(
            "/pipeline",
            json={
                "initial_prompt": "Черновик статьи про Kubernetes",
                "pipeline": ["summarizer", "writer"],
            },
            headers=AUTH_HEADERS,
        )

        assert response.status_code == 200
        assert response.json()["result"] == "Финальная статья после writer."


def test_protected_endpoint_requires_bearer_token():
    app = create_app()
    with TestClient(app) as client:
        response = client.get("/")

        assert response.status_code == 401


def test_health_endpoint_is_public():
    app = create_app()
    with TestClient(app) as client:
        response = client.get("/health")

        assert response.status_code == 200
