from src.core.errors import OutlineParseError
from src.features.articles.parser import parse_outline_markdown


def test_parse_outline_markdown_success():
    title, sections = parse_outline_markdown(
        outline_markdown=(
            "# Kubernetes для Python-команд\n"
            "1. Зачем это нужно :: Почему orchestration важен для production.\n"
            "2. Базовые сущности :: Что такое pods, deployments и services.\n"
        ),
        fallback_title="Fallback",
    )

    assert title == "Kubernetes для Python-команд"
    assert len(sections) == 2
    assert sections[0].title == "Зачем это нужно"


def test_parse_outline_markdown_raises_for_invalid_format():
    try:
        parse_outline_markdown("Просто текст без структуры", "Fallback")
    except OutlineParseError as exc:
        assert exc.code == "OUTLINE_PARSE_FAILED"
    else:
        raise AssertionError("OutlineParseError was not raised")


def test_parse_outline_markdown_accepts_numbered_lines_without_double_colons():
    title, sections = parse_outline_markdown(
        outline_markdown=(
            "# Kubernetes для Python-команд\n"
            "1) Зачем это нужно\n"
            "Почему orchestration важен для production.\n"
            "2) Базовые сущности — Pods, Deployments и Services.\n"
        ),
        fallback_title="Fallback",
    )

    assert title == "Kubernetes для Python-команд"
    assert len(sections) == 2
    assert sections[0].title == "Зачем это нужно"
    assert "Почему orchestration важен" in sections[0].description
    assert sections[1].title == "Базовые сущности"


def test_parse_outline_markdown_accepts_bullet_list_sections():
    _, sections = parse_outline_markdown(
        outline_markdown=(
            "# Статья\n"
            "- Контейнеризация: что она решает\n"
            "- Kubernetes — orchestration layer\n"
        ),
        fallback_title="Fallback",
    )

    assert [section.index for section in sections] == [1, 2]
    assert sections[0].title == "Контейнеризация"
