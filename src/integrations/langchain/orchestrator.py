from langchain_core.prompts import PromptTemplate
from langchain_core.runnables import RunnableLambda

from src.core.errors import EmptyModelResponseError
from src.integrations.llm_server import LLMClient


class LangChainAgentOrchestrator:
    """LangChain-based orchestration over LLM agent aliases."""

    def __init__(self, llm_client: LLMClient):
        self.client = llm_client

    def invoke(
        self,
        agent_name: str,
        system_prompt: str,
        user_prompt: str,
        temperature: float,
        max_tokens: int,
    ) -> str:
        prompt = PromptTemplate.from_template(
            "Инструкции:\n{system_prompt}\n\nЗапрос:\n{user_prompt}"
        )
        chain = prompt | RunnableLambda(
            lambda prompt_value: self._invoke_model(
                agent_name=agent_name,
                prompt_value=prompt_value,
                temperature=temperature,
                max_tokens=max_tokens,
            )
        )
        result = chain.invoke(
            {
                "system_prompt": system_prompt,
                "user_prompt": user_prompt,
            }
        )
        if not result.strip():
            raise EmptyModelResponseError("Model returned an empty response.")
        return result.strip()

    def _invoke_model(self, agent_name: str, prompt_value, temperature: float, max_tokens: int) -> str:
        return self.client.generate(
            model=agent_name,
            prompt=prompt_value.to_string(),
            temperature=temperature,
            max_tokens=max_tokens,
        )

    def run_pipeline(
        self,
        steps: list[dict[str, str]],
        initial_prompt: str,
        temperature: float,
        max_tokens: int,
    ) -> str:
        def invoke_step(state: dict, step: dict) -> dict:
            result = self.invoke(
                agent_name=step["agent_name"],
                system_prompt=step["system_prompt"],
                user_prompt=f"Обработай текст:\n{state['text']}",
                temperature=temperature,
                max_tokens=max_tokens,
            )
            return {"text": result}

        chain = RunnableLambda(lambda text: {"text": text})
        for step in steps:
            chain = chain | RunnableLambda(lambda state, step=step: invoke_step(state, step))

        result = chain.invoke(initial_prompt)
        return result["text"].strip()
