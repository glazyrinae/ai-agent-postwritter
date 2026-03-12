from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = Field(default="Multi-Agent System API")
    app_version: str = Field(default="1.0.0")
    api_host: str = Field(default="0.0.0.0")
    api_port: int = Field(default=8080)
    api_bearer_token: str = Field(default="change-me")

    vllm_url: str = Field(default="http://localhost:8000")
    default_model: str = Field(default="cotype-nano")
    default_temperature: float = Field(default=0.3)
    max_tokens: int = Field(default=2048)

    article_default_sections: int = Field(default=5)
    article_outline_max_tokens: int = Field(default=800)
    article_chapter_max_tokens: int = Field(default=1700)
    article_summary_max_tokens: int = Field(default=400)
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


settings = Settings()
