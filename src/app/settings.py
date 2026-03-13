import os

from pydantic import AliasChoices, Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = Field(default="Multi-Agent System API")
    app_version: str = Field(default="1.0.0")
    api_host: str = Field(default="0.0.0.0")
    api_port: int = Field(default=8080)
    api_bearer_token: str = Field(default="change-me")
    database_url: str = Field(default="")
    postgres_host: str = Field(default="db")
    postgres_port: int = Field(default=5432)
    postgres_db: str = Field(default="article_service")
    postgres_user: str = Field(default="article_service")
    postgres_password: str = Field(default="article_service")

    llm_backend: str = Field(default="ollama", validation_alias=AliasChoices("LLM_BACKEND"))
    llm_base_url: str = Field(
        default="",
        validation_alias=AliasChoices("LLM_BASE_URL", "VLLM_URL"),
    )
    llm_request_timeout_seconds: int = Field(
        default=1800,
        validation_alias=AliasChoices("LLM_REQUEST_TIMEOUT_SECONDS"),
    )
    default_model: str = Field(
        default="cotype-nano",
        validation_alias=AliasChoices("LLM_DEFAULT_MODEL", "DEFAULT_MODEL"),
    )
    default_temperature: float = Field(default=0.3, validation_alias=AliasChoices("DEFAULT_TEMPERATURE"))
    max_tokens: int = Field(default=2048, validation_alias=AliasChoices("MAX_TOKENS"))

    article_default_sections: int = Field(default=5)
    article_default_target_audience: str = Field(default="IT engineers")
    article_default_style: str = Field(default="практический технический блог")
    article_default_include_code_examples: bool = Field(default=True)
    article_outline_max_tokens: int = Field(default=800)
    article_chapter_max_tokens: int = Field(default=1700)
    article_summary_max_tokens: int = Field(default=400)
    article_proofread_max_tokens: int = Field(default=2600)
    article_min_section_chars: int = Field(default=200)
    article_context_sections_limit: int = Field(default=3)

    available_agents: dict[str, str] = Field(
        default_factory=lambda: {
            "editor": "editor",
            "summarizer": "summarizer",
            "writer": "writer",
        }
    )

    model_config = SettingsConfigDict(env_file=".env", case_sensitive=False)

    @model_validator(mode="after")
    def apply_compatibility_aliases(self) -> "Settings":
        if not self.llm_base_url:
            self.llm_base_url = (
                os.getenv("LLM_BASE_URL")
                or os.getenv("VLLM_URL")
                or "http://localhost:11434"
            ).strip()
        self.llm_backend = self.llm_backend.strip().lower() or "ollama"
        if self.llm_backend not in {"ollama", "vllm"}:
            self.llm_backend = "ollama"
        return self


settings = Settings()
