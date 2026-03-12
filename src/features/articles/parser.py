import re

from src.core.errors import OutlineParseError
from src.features.articles.schemas import ParsedOutlineSection


TITLE_PATTERN = re.compile(r"^\s*#\s+(.+?)\s*$")
NUMBERED_SECTION_PATTERN = re.compile(r"^\s*(\d+)[\.\)]\s+(.+?)\s*$")
BULLET_SECTION_PATTERN = re.compile(r"^\s*[-*]\s+(.+?)\s*$")


def _split_title_and_description(text: str) -> tuple[str, str]:
    cleaned = text.strip()
    for delimiter in ("::", " — ", " – ", " - ", ": "):
        if delimiter in cleaned:
            title, description = cleaned.split(delimiter, 1)
            return title.strip(), description.strip()
    return cleaned, ""


def _append_section(
    sections: list[ParsedOutlineSection],
    index: int,
    raw_title: str,
    description_lines: list[str],
) -> None:
    title, inline_description = _split_title_and_description(raw_title)
    description_parts = [part.strip() for part in [inline_description, *description_lines] if part.strip()]
    description = " ".join(description_parts).strip()
    if not title:
        return
    if not description:
        description = "Краткое описание раздела не было выделено отдельно."
    sections.append(
        ParsedOutlineSection(
            index=index,
            title=title,
            description=description,
        )
    )


def parse_outline_markdown(outline_markdown: str, fallback_title: str) -> tuple[str, list[ParsedOutlineSection]]:
    title = fallback_title.strip()
    sections: list[ParsedOutlineSection] = []
    pending_title = ""
    pending_index: int | None = None
    pending_description_lines: list[str] = []

    def flush_pending() -> None:
        nonlocal pending_title, pending_index, pending_description_lines
        if pending_title and pending_index is not None:
            _append_section(
                sections=sections,
                index=pending_index,
                raw_title=pending_title,
                description_lines=pending_description_lines,
            )
        pending_title = ""
        pending_index = None
        pending_description_lines = []

    for raw_line in outline_markdown.splitlines():
        line = raw_line.strip()
        if not line:
            continue

        title_match = TITLE_PATTERN.match(line)
        if title_match:
            title = title_match.group(1).strip()
            continue

        numbered_match = NUMBERED_SECTION_PATTERN.match(line)
        if numbered_match:
            flush_pending()
            pending_index = int(numbered_match.group(1))
            pending_title = numbered_match.group(2).strip()
            continue

        bullet_match = BULLET_SECTION_PATTERN.match(line)
        if bullet_match:
            flush_pending()
            pending_index = len(sections) + 1
            pending_title = bullet_match.group(1).strip()
            continue

        if pending_title:
            pending_description_lines.append(line)

    flush_pending()

    if not sections:
        raise OutlineParseError(
            message="Could not parse outline into sections.",
            details={"expected_format": "1. Section title :: short description"},
        )

    return title, sections
