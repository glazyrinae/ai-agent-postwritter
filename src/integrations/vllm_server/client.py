from src.integrations.llm_server import LLMClient


class VLLMClient(LLMClient):
    """Deprecated compatibility alias around the new generic LLM client."""

    def __init__(self, base_url: str, default_model: str, request_timeout_seconds: int = 1800):
        super().__init__(
            backend="vllm",
            base_url=base_url,
            default_model=default_model,
            request_timeout_seconds=request_timeout_seconds,
        )
