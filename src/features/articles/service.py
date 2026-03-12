from src.app.settings import Settings
from src.core.errors import ConfigurationError, EmptyModelResponseError
from src.features.articles.parser import parse_outline_markdown
from src.features.articles.prompts import (
    build_blog_system_prompt,
    build_conclusion_prompt,
    build_outline_prompt,
    build_section_prompt,
    build_summary_prompt,
)
from src.features.articles.schemas import (
    ArticleGenerateRequest,
    ArticleGenerateResponse,
    ArticleSectionResult,
    OutlineRequest,
    OutlineResponse,
    ParsedOutlineSection,
)
from src.integrations.langchain import LangChainAgentOrchestrator
from src.integrations.vllm_server import VLLMClient


class ArticleService:
    def __init__(self, settings: Settings, vllm_client: VLLMClient):
        self.settings = settings
        self.vllm_client = vllm_client
        self.orchestrator = LangChainAgentOrchestrator(vllm_client=vllm_client)
        if "writer" not in self.settings.available_agents:
            raise ConfigurationError("Agent alias 'writer' must be configured in available_agents.")
        self.writer_agent = self.settings.available_agents["writer"]
        self.summarizer_agent = self.settings.available_agents.get("summarizer", self.writer_agent)

    def generate_outline(self, request: OutlineRequest) -> OutlineResponse:
        outline_markdown = self._invoke_agent(
            agent_name=self.writer_agent,
            prompt=build_outline_prompt(
                topic=request.topic,
                desired_sections_count=request.desired_sections_count,
                include_code_examples=request.include_code_examples,
            ),
            system_prompt=build_blog_system_prompt(
                target_audience=request.target_audience,
                style=request.style,
            ),
            temperature=0.3,
            max_tokens=self.settings.article_outline_max_tokens,
        )
        title, sections = self.parse_outline(
            outline_markdown=outline_markdown,
            fallback_title=request.topic,
        )
        return OutlineResponse(title=title, outline_markdown=outline_markdown, sections=sections)

    def parse_outline(self, outline_markdown: str, fallback_title: str) -> tuple[str, list[ParsedOutlineSection]]:
        return parse_outline_markdown(outline_markdown=outline_markdown, fallback_title=fallback_title)

    def generate_section(
        self,
        topic: str,
        outline_markdown: str,
        section: ParsedOutlineSection,
        target_audience: str,
        style: str,
        previous_summaries: list[str],
        include_code_examples: bool,
        chapter_max_tokens: int,
    ) -> str:
        section_text = self._invoke_agent(
            agent_name=self.writer_agent,
            prompt=build_section_prompt(
                topic=topic,
                outline_markdown=outline_markdown,
                section_title=section.title,
                section_description=section.description,
                previous_summaries=previous_summaries[-self.settings.article_context_sections_limit :],
                include_code_examples=include_code_examples,
            ),
            system_prompt=build_blog_system_prompt(
                target_audience=target_audience,
                style=style,
            ),
            temperature=0.4,
            max_tokens=chapter_max_tokens,
        )
        if len(section_text.strip()) < self.settings.article_min_section_chars:
            raise EmptyModelResponseError(
                message="Generated section is too short to be useful.",
                details={"section": section.title, "min_chars": self.settings.article_min_section_chars},
            )
        return section_text

    def summarize_section_for_context(self, section_title: str, section_text: str) -> str:
        return self._invoke_agent(
            agent_name=self.summarizer_agent,
            prompt=build_summary_prompt(section_title=section_title, section_text=section_text),
            system_prompt="Ты сжимаешь текст до плотного технического summary без потери ключевых идей.",
            temperature=0.2,
            max_tokens=self.settings.article_summary_max_tokens,
        )

    def generate_conclusion(
        self,
        topic: str,
        outline_markdown: str,
        section_summaries: list[str],
        target_audience: str,
        style: str,
    ) -> str:
        return self._invoke_agent(
            agent_name=self.writer_agent,
            prompt=build_conclusion_prompt(
                topic=topic,
                outline_markdown=outline_markdown,
                section_summaries=section_summaries,
            ),
            system_prompt=build_blog_system_prompt(
                target_audience=target_audience,
                style=style,
            ),
            temperature=0.4,
            max_tokens=self.settings.article_summary_max_tokens,
        )

    def compile_article(
        self,
        title: str,
        sections: list[ArticleSectionResult],
        conclusion: str,
    ) -> str:
        parts = [f"# {title}", ""]
        for section in sections:
            parts.append(f"## {section.title}")
            parts.append("")
            parts.append(section.content.strip())
            parts.append("")
        parts.append("## Заключение")
        parts.append("")
        parts.append(conclusion.strip())
        return "\n".join(parts).strip()

    def generate_article(self, request: ArticleGenerateRequest) -> ArticleGenerateResponse:
        if request.outline_markdown:
            outline_markdown = request.outline_markdown
            title, parsed_sections = self.parse_outline(
                outline_markdown=outline_markdown,
                fallback_title=request.topic,
            )
        else:
            outline = self.generate_outline(
                OutlineRequest(
                    topic=request.topic,
                    target_audience=request.target_audience,
                    style=request.style,
                    desired_sections_count=request.desired_sections_count,
                    include_code_examples=request.include_code_examples,
                )
            )
            title = outline.title
            outline_markdown = outline.outline_markdown
            parsed_sections = outline.sections

        chapter_max_tokens = request.chapter_max_tokens or self.settings.article_chapter_max_tokens
        previous_summaries: list[str] = []
        generated_sections: list[ArticleSectionResult] = []

        for section in parsed_sections:
            content = self.generate_section(
                topic=request.topic,
                outline_markdown=outline_markdown,
                section=section,
                target_audience=request.target_audience,
                style=request.style,
                previous_summaries=previous_summaries,
                include_code_examples=request.include_code_examples,
                chapter_max_tokens=chapter_max_tokens,
            )
            summary = self.summarize_section_for_context(section_title=section.title, section_text=content)
            previous_summaries.append(summary)
            generated_sections.append(
                ArticleSectionResult(
                    title=section.title,
                    description=section.description,
                    content=content,
                    summary=summary,
                )
            )

        conclusion = self.generate_conclusion(
            topic=request.topic,
            outline_markdown=outline_markdown,
            section_summaries=previous_summaries,
            target_audience=request.target_audience,
            style=request.style,
        )
        article_markdown = self.compile_article(
            title=title,
            sections=generated_sections,
            conclusion=conclusion,
        )
        return ArticleGenerateResponse(
            title=title,
            outline_markdown=outline_markdown,
            sections=generated_sections,
            article_markdown=article_markdown,
        )

    def _invoke_agent(
        self,
        agent_name: str,
        prompt: str,
        system_prompt: str,
        temperature: float,
        max_tokens: int,
    ) -> str:
        return self.orchestrator.invoke(
            agent_name=agent_name,
            system_prompt=system_prompt,
            user_prompt=prompt,
            temperature=temperature,
            max_tokens=max_tokens,
        )
