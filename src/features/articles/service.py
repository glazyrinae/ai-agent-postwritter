import json
import re

from src.app.settings import Settings
from src.core.errors import ConfigurationError, EmptyModelResponseError, InvalidStateError, OutlineParseError
from src.features.articles.parser import parse_outline_markdown
from src.features.articles.prompts import (
    build_blog_system_prompt,
    build_conclusion_prompt,
    build_outline_prompt,
    build_proofreading_prompt,
    build_section_prompt,
    build_summary_prompt,
)
from src.features.articles.repository import ArticleRunRepository, RUN_STATUS_COMPLETED
from src.features.articles.schemas import (
    ArticleGenerateRequest,
    ArticleGenerateResponse,
    ArticleRunSectionStatus,
    ArticleRunStatusResponse,
    ArticleSectionResult,
    OutlineRequest,
    OutlineResponse,
    ParsedOutlineSection,
)
from src.integrations.langchain import LangChainAgentOrchestrator
from src.integrations.llm_server import LLMClient


class ArticleService:
    FORBIDDEN_PHRASES = (
        "привет",
        "я могу помочь",
        "как ии",
        "давай разберем",
        "надеюсь, это поможет",
        "уточните ваш запрос",
        "уточните запрос",
        "конечно, я могу помочь",
    )
    OUTLINE_ASSISTANT_PREFIXES = (
        "как я могу помочь",
        "чем могу помочь",
        "я могу помочь",
        "конечно",
        "привет",
    )

    def __init__(self, settings: Settings, llm_client: LLMClient, repository: ArticleRunRepository):
        self.settings = settings
        self.llm_client = llm_client
        self.repository = repository
        self.orchestrator = LangChainAgentOrchestrator(llm_client=llm_client)
        if "writer" not in self.settings.available_agents:
            raise ConfigurationError("Agent alias 'writer' must be configured in available_agents.")
        self.writer_agent = self.settings.available_agents["writer"]
        self.summarizer_agent = self.settings.available_agents.get("summarizer", self.writer_agent)
        self.editor_agent = self.settings.available_agents.get("editor", self.writer_agent)

    def generate_outline(self, request: OutlineRequest) -> OutlineResponse:
        raw_outline = self._invoke_agent(
            agent_name=self.settings.default_model or self.writer_agent,
            prompt=build_outline_prompt(
                topic=request.topic,
                desired_sections_count=request.desired_sections_count,
                include_code_examples=request.include_code_examples,
            ),
            system_prompt=build_blog_system_prompt(
                target_audience=request.target_audience,
                style=request.style,
            ),
            temperature=0.2,
            max_tokens=self.settings.article_outline_max_tokens,
        )
        title, sections = self._parse_structured_outline(
            raw_outline=raw_outline,
            fallback_title=request.topic,
            expected_sections_count=request.desired_sections_count,
        )
        outline_markdown = self._build_outline_markdown(title=title, sections=sections)
        return OutlineResponse(title=title, outline_markdown=outline_markdown, sections=sections)

    def _parse_structured_outline(
        self,
        raw_outline: str,
        fallback_title: str,
        expected_sections_count: int,
    ) -> tuple[str, list[ParsedOutlineSection]]:
        candidate = raw_outline.strip()
        lowered = candidate.lower()
        if any(lowered.startswith(prefix) for prefix in self.OUTLINE_ASSISTANT_PREFIXES):
            raise OutlineParseError(
                message="Could not parse outline into sections.",
                details={
                    "expected_format": '{"title":"...","sections":[{"title":"...","description":"..."}]}',
                    "raw_outline_preview": raw_outline[:600],
                    "reason": "model returned assistant-style response instead of structured outline",
                },
            )
        if "```" in candidate:
            parts = candidate.split("```")
            fenced = [part for part in parts if "{" in part and "}" in part]
            if fenced:
                candidate = fenced[0]
                if candidate.lstrip().startswith("json"):
                    candidate = candidate.lstrip()[4:].strip()
        start = candidate.find("{")
        end = candidate.rfind("}")
        if start != -1 and end != -1 and end > start:
            candidate = candidate[start : end + 1]

        try:
            payload = json.loads(candidate)
        except json.JSONDecodeError as exc:
            fallback_parsed = self._parse_structured_outline_fallback(
                candidate=candidate,
                fallback_title=fallback_title,
                expected_sections_count=expected_sections_count,
            )
            if fallback_parsed is None:
                raise OutlineParseError(
                    message="Could not parse outline into sections.",
                    details={
                        "expected_format": '{"title":"...","sections":[{"title":"...","description":"..."}]}',
                        "raw_outline_preview": raw_outline[:600],
                        "reason": str(exc),
                    },
                ) from exc
            return fallback_parsed

        title = str(payload.get("title") or fallback_title).strip()
        raw_sections = payload.get("sections")
        if not isinstance(raw_sections, list):
            raise OutlineParseError(
                message="Could not parse outline into sections.",
                details={
                    "expected_format": '{"title":"...","sections":[{"title":"...","description":"..."}]}',
                    "raw_outline_preview": raw_outline[:600],
                    "reason": "sections must be a list",
                },
            )

        sections: list[ParsedOutlineSection] = []
        for index, item in enumerate(raw_sections, start=1):
            if not isinstance(item, dict):
                continue
            section_title = str(item.get("title") or "").strip()
            section_description = str(item.get("description") or "").strip()
            if not section_title or not section_description:
                continue
            sections.append(
                ParsedOutlineSection(
                    index=index,
                    title=section_title,
                    description=section_description,
                )
            )

        if len(sections) != expected_sections_count:
            raise OutlineParseError(
                message="Could not parse outline into sections.",
                details={
                    "expected_sections_count": expected_sections_count,
                    "actual_sections_count": len(sections),
                    "raw_outline_preview": raw_outline[:600],
                },
            )

        return title, sections

    def _parse_structured_outline_fallback(
        self,
        candidate: str,
        fallback_title: str,
        expected_sections_count: int,
    ) -> tuple[str, list[ParsedOutlineSection]] | None:
        title_match = re.search(r'"title"\s*:\s*"([^"]+)"', candidate)
        title = (title_match.group(1).strip() if title_match else fallback_title) or fallback_title
        section_matches = re.findall(
            r'\{\s*"title"\s*:\s*"([^"]+)"\s*,\s*"description"\s*:\s*"([^"]+)"\s*\}',
            candidate,
            flags=re.DOTALL,
        )
        if len(section_matches) != expected_sections_count:
            return None

        sections = [
            ParsedOutlineSection(
                index=index,
                title=section_title.strip(),
                description=section_description.strip(),
            )
            for index, (section_title, section_description) in enumerate(section_matches, start=1)
        ]
        return title, sections

    def _build_outline_markdown(self, title: str, sections: list[ParsedOutlineSection]) -> str:
        lines = [f"# {title}"]
        for section in sections:
            lines.append(f"{section.index}. {section.title} :: {section.description}")
        return "\n".join(lines)

    def parse_outline(self, outline_markdown: str, fallback_title: str) -> tuple[str, list[ParsedOutlineSection]]:
        return parse_outline_markdown(outline_markdown=outline_markdown, fallback_title=fallback_title)

    def get_run_status(self, run_id: str) -> ArticleRunStatusResponse:
        run = self.repository.get_run(run_id)
        return ArticleRunStatusResponse(
            run_id=run["id"],
            status=run["status"],
            topic=run["topic"],
            title=run["title"],
            current_step=run["current_step"],
            last_error=run["last_error"],
            outline_markdown=run["outline_markdown"],
            sections=[
                ArticleRunSectionStatus(
                    index=section["section_index"],
                    title=section["title"],
                    description=section["description"],
                    status=section["status"],
                    content=section["content"],
                    summary=section["summary"],
                )
                for section in run["sections"]
            ],
        )

    def get_run_result(self, run_id: str) -> ArticleGenerateResponse:
        run = self.repository.get_run(run_id)
        if run["status"] != RUN_STATUS_COMPLETED:
            raise InvalidStateError(
                "Article run is not completed yet.",
                details={"run_id": run_id, "status": run["status"]},
            )
        return ArticleGenerateResponse(
            run_id=run["id"],
            status=run["status"],
            title=run["title"] or run["topic"],
            outline_markdown=run["outline_markdown"] or "",
            sections=[
                ArticleSectionResult(
                    title=section["title"],
                    description=section["description"],
                    content=section["content"] or "",
                    summary=section["summary"] or "",
                )
                for section in run["sections"]
            ],
            article_markdown=run["article_markdown"] or "",
        )

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
        section_text = self._sanitize_generated_text(
            self._invoke_agent(
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
            ),
        )
        if len(section_text.strip()) < self.settings.article_min_section_chars:
            raise EmptyModelResponseError(
                message="Generated section is too short to be useful.",
                details={"section": section.title, "min_chars": self.settings.article_min_section_chars},
            )
        return section_text

    def summarize_section_for_context(self, section_title: str, section_text: str) -> str:
        return self._sanitize_generated_text(self._invoke_agent(
            agent_name=self.summarizer_agent,
            prompt=build_summary_prompt(section_title=section_title, section_text=section_text),
            system_prompt=(
                "Ты сжимаешь текст до плотного технического summary без потери ключевых идей. "
                "Не используй приветствия, не предлагай помощь, не объясняй, что ты делаешь."
            ),
            temperature=0.2,
            max_tokens=self.settings.article_summary_max_tokens,
        ))

    def generate_conclusion(
        self,
        topic: str,
        outline_markdown: str,
        section_summaries: list[str],
        target_audience: str,
        style: str,
    ) -> str:
        return self._sanitize_generated_text(self._invoke_agent(
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
        ))

    def proofread_article(self, title: str, article_markdown: str) -> str:
        return self._sanitize_generated_text(
            self._invoke_agent(
                agent_name=self.editor_agent,
                prompt=build_proofreading_prompt(title=title, article_markdown=article_markdown),
                system_prompt=(
                    "Ты технический редактор. Верни только улучшенный markdown статьи без вступления, "
                    "без объяснения правок и без assistant-tone."
                ),
                temperature=0.2,
                max_tokens=self.settings.article_proofread_max_tokens,
            )
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
        target_audience = self.settings.article_default_target_audience
        style = self.settings.article_default_style
        desired_sections_count = self.settings.article_default_sections
        include_code_examples = self.settings.article_default_include_code_examples
        chapter_max_tokens = self.settings.article_chapter_max_tokens

        run_id = self.repository.create_run(
            topic=request.topic,
            target_audience=target_audience,
            style=style,
            desired_sections_count=desired_sections_count,
            include_code_examples=include_code_examples,
            chapter_max_tokens=chapter_max_tokens,
        )

        try:
            outline = self.generate_outline(
                OutlineRequest(
                    topic=request.topic,
                    target_audience=target_audience,
                    style=style,
                    desired_sections_count=desired_sections_count,
                    include_code_examples=include_code_examples,
                )
            )
            title = outline.title
            outline_markdown = outline.outline_markdown
            parsed_sections = outline.sections
            self.repository.save_outline(
                run_id,
                title,
                outline_markdown,
                [section.model_dump() for section in parsed_sections],
            )

            previous_summaries: list[str] = []
            generated_sections: list[ArticleSectionResult] = []

            for section in parsed_sections:
                content = self.generate_section(
                    topic=request.topic,
                    outline_markdown=outline_markdown,
                    section=section,
                    target_audience=target_audience,
                    style=style,
                    previous_summaries=previous_summaries,
                    include_code_examples=include_code_examples,
                    chapter_max_tokens=chapter_max_tokens,
                )
                self.repository.save_section_content(run_id, section.index, content)
                summary = self.summarize_section_for_context(section_title=section.title, section_text=content)
                self.repository.save_section_summary(run_id, section.index, summary)
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
                target_audience=target_audience,
                style=style,
            )
            self.repository.save_conclusion(run_id, conclusion)
            draft_article_markdown = self.compile_article(
                title=title,
                sections=generated_sections,
                conclusion=conclusion,
            )
            article_markdown = self.proofread_article(title=title, article_markdown=draft_article_markdown)
            self.repository.complete_run(run_id, article_markdown)
            return ArticleGenerateResponse(
                run_id=run_id,
                status=RUN_STATUS_COMPLETED,
                title=title,
                outline_markdown=outline_markdown,
                sections=generated_sections,
                article_markdown=article_markdown,
            )
        except Exception as exc:
            try:
                self.repository.fail_run(run_id, "failed", str(exc))
            except Exception:
                pass
            raise

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

    def _sanitize_generated_text(self, text: str) -> str:
        cleaned = text.strip()
        lines = [line for line in cleaned.splitlines() if line.strip()]
        while lines:
            lowered = lines[0].strip().lower()
            if any(phrase in lowered for phrase in self.FORBIDDEN_PHRASES):
                lines.pop(0)
                continue
            break
        return "\n".join(lines).strip() or cleaned
