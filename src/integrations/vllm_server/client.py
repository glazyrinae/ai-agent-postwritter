from collections.abc import Iterator

from openai import OpenAI

from src.core.errors import UpstreamServiceError


class VLLMClient:
    """OpenAI-compatible thin client around the vLLM server."""

    def __init__(self, base_url: str, default_model: str):
        self.client = OpenAI(base_url=f"{base_url}/v1", api_key="EMPTY")
        self.base_url = base_url
        self.default_model = default_model

    def chat(
        self,
        model: str,
        messages: list[dict[str, str]],
        temperature: float,
        max_tokens: int,
        stream: bool = False,
        **kwargs,
    ):
        try:
            return self.client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
                stream=stream,
                **kwargs,
            )
        except Exception as exc:
            raise UpstreamServiceError(
                message="vLLM request failed",
                details={"base_url": self.base_url, "reason": str(exc)},
            ) from exc

    def stream(
        self,
        model: str,
        messages: list[dict[str, str]],
        temperature: float,
        max_tokens: int,
        **kwargs,
    ) -> Iterator[str]:
        stream = self.chat(
            model=model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
            stream=True,
            **kwargs,
        )
        for chunk in stream:
            content = chunk.choices[0].delta.content
            if content:
                yield content

    def list_models(self) -> list[str]:
        try:
            return [model.id for model in self.client.models.list().data]
        except Exception as exc:
            raise UpstreamServiceError(
                message="Failed to fetch models from vLLM",
                details={"base_url": self.base_url, "reason": str(exc)},
            ) from exc
