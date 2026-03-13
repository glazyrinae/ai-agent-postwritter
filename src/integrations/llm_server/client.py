import json
from collections.abc import Iterator
from urllib import request as urllib_request

from openai import OpenAI

from src.core.errors import UpstreamServiceError


class LLMClient:
    """Runtime-selectable client for Ollama and vLLM backends."""

    def __init__(self, backend: str, base_url: str, default_model: str, request_timeout_seconds: int):
        self.backend = backend.strip().lower()
        self.base_url = base_url.rstrip("/")
        self.default_model = default_model
        self.request_timeout_seconds = request_timeout_seconds
        self.openai_client = OpenAI(
            base_url=self._build_openai_base_url(self.base_url),
            api_key="EMPTY",
            timeout=request_timeout_seconds,
        )

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
            return self.openai_client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
                stream=stream,
                **kwargs,
            )
        except Exception as exc:
            raise UpstreamServiceError(
                message="LLM chat request failed",
                details={"base_url": self.base_url, "backend": self.backend, "reason": str(exc)},
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

    def generate(
        self,
        model: str,
        prompt: str,
        temperature: float,
        max_tokens: int,
    ) -> str:
        if self.backend == "ollama":
            return self._ollama_generate(
                model=model,
                prompt=prompt,
                temperature=temperature,
                max_tokens=max_tokens,
            )

        response = self.chat(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            temperature=temperature,
            max_tokens=max_tokens,
        )
        return (response.choices[0].message.content or "").strip()

    def list_models(self) -> list[str]:
        if self.backend == "ollama":
            return self._ollama_list_models()

        try:
            return [model.id for model in self.openai_client.models.list().data]
        except Exception as exc:
            raise UpstreamServiceError(
                message="Failed to fetch models from upstream backend",
                details={"base_url": self.base_url, "backend": self.backend, "reason": str(exc)},
            ) from exc

    def _ollama_generate(self, model: str, prompt: str, temperature: float, max_tokens: int) -> str:
        payload = json.dumps(
            {
                "model": model,
                "prompt": prompt,
                "stream": False,
                "options": {
                    "temperature": temperature,
                    "num_predict": max_tokens,
                },
            }
        ).encode("utf-8")
        req = urllib_request.Request(
            url=f"{self.base_url}/api/generate",
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib_request.urlopen(req, timeout=self.request_timeout_seconds) as response:
                body = json.loads(response.read().decode("utf-8"))
        except Exception as exc:
            raise UpstreamServiceError(
                message="Raw generate request failed",
                details={"base_url": self.base_url, "backend": self.backend, "reason": str(exc)},
            ) from exc

        return str(body.get("response") or "").strip()

    def _ollama_list_models(self) -> list[str]:
        req = urllib_request.Request(
            url=f"{self.base_url}/api/tags",
            headers={"Content-Type": "application/json"},
            method="GET",
        )
        try:
            with urllib_request.urlopen(req, timeout=self.request_timeout_seconds) as response:
                body = json.loads(response.read().decode("utf-8"))
        except Exception as exc:
            raise UpstreamServiceError(
                message="Failed to fetch models from upstream backend",
                details={"base_url": self.base_url, "backend": self.backend, "reason": str(exc)},
            ) from exc

        models = body.get("models") or []
        return [str(model.get("name") or "").strip() for model in models if model.get("name")]

    @staticmethod
    def _build_openai_base_url(base_url: str) -> str:
        return base_url if base_url.endswith("/v1") else f"{base_url}/v1"
