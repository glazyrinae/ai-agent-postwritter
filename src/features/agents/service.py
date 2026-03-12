from collections.abc import Iterator

from src.app.settings import Settings
from src.integrations.langchain import LangChainAgentOrchestrator
from src.integrations.vllm_server import VLLMClient


AGENT_SYSTEM_PROMPTS = {
    "editor": "Ты редактор. Исправляй грамматические и стилистические ошибки.",
    "summarizer": "Ты суммаризатор. Кратко излагай суть текста.",
    "writer": "Ты писатель. Пиши развернутые тексты по плану.",
}


class AgentService:
    def __init__(self, settings: Settings, vllm_client: VLLMClient):
        self.settings = settings
        self.vllm_client = vllm_client
        self.orchestrator = LangChainAgentOrchestrator(vllm_client=vllm_client)

    def ensure_agent_name(self, agent_name: str) -> str:
        if agent_name not in self.settings.available_agents:
            available = ", ".join(self.settings.available_agents.keys())
            raise ValueError(f"Agent '{agent_name}' not found. Available agents: {available}")
        return self.settings.available_agents[agent_name]

    def call_agent(
        self,
        agent_name: str,
        prompt: str,
        system_prompt: str | None,
        temperature: float,
        max_tokens: int,
        **kwargs,
    ) -> str:
        return self.orchestrator.invoke(
            agent_name=agent_name,
            system_prompt=system_prompt or AGENT_SYSTEM_PROMPTS.get(agent_name, ""),
            user_prompt=prompt,
            temperature=temperature,
            max_tokens=max_tokens,
        )

    def stream_agent(
        self,
        agent_name: str,
        prompt: str,
        system_prompt: str | None,
        temperature: float,
        max_tokens: int,
        **kwargs,
    ) -> Iterator[str]:
        messages: list[dict[str, str]] = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})
        return self.vllm_client.stream(
            model=agent_name,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
            **kwargs,
        )

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
