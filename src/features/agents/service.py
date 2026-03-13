from src.app.settings import Settings
from src.core.errors import EmptyModelResponseError
from src.integrations.langchain import LangChainAgentOrchestrator
from src.integrations.llm_server import LLMClient


AGENT_SYSTEM_PROMPTS = {
    "editor": "Ты редактор. Исправляй грамматические и стилистические ошибки.",
    "summarizer": "Ты суммаризатор. Кратко излагай суть текста.",
    "writer": "Ты писатель. Пиши развернутые тексты по плану.",
}


class AgentService:
    def __init__(self, settings: Settings, llm_client: LLMClient):
        self.settings = settings
        self.llm_client = llm_client
        self.orchestrator = LangChainAgentOrchestrator(llm_client=llm_client)

    def ensure_agent_name(self, agent_name: str) -> str:
        if agent_name not in self.settings.available_agents:
            available = ", ".join(self.settings.available_agents.keys())
            raise ValueError(f"Agent '{agent_name}' not found. Available agents: {available}")
        return self.settings.available_agents[agent_name]

    def run_pipeline(self, pipeline: list[str], initial_prompt: str) -> str:
        steps: list[dict[str, str]] = []
        for agent_name in pipeline:
            resolved_agent = self.ensure_agent_name(agent_name)
            steps.append(
                {
                    "agent_name": resolved_agent,
                    "system_prompt": AGENT_SYSTEM_PROMPTS.get(agent_name, ""),
                }
            )
        return self.orchestrator.run_pipeline(
            steps=steps,
            initial_prompt=initial_prompt,
            temperature=self.settings.default_temperature,
            max_tokens=self.settings.max_tokens,
        )

    def debug_prompt(self, prompt: str, model: str | None = None) -> tuple[str, str]:
        resolved_model = (model or self.settings.default_model).strip()
        content = self.llm_client.generate(
            model=resolved_model,
            prompt=prompt,
            temperature=self.settings.default_temperature,
            max_tokens=self.settings.max_tokens,
        )
        if not content.strip():
            raise EmptyModelResponseError("Model returned an empty response.")
        return resolved_model, content.strip()
