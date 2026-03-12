from src.features.articles.prompts import (
    build_conclusion_prompt,
    build_outline_prompt,
    build_section_prompt,
)


def test_outline_prompt_contains_expected_contract():
    prompt = build_outline_prompt(
        topic="Kubernetes",
        desired_sections_count=5,
        include_code_examples=True,
    )

    assert "ровно 5" in prompt
    assert "1. Название раздела :: краткое описание раздела" in prompt


def test_section_prompt_includes_previous_summaries():
    prompt = build_section_prompt(
        topic="Kubernetes",
        outline_markdown="# Title\n1. One :: Desc",
        section_title="Control plane",
        section_description="Что делает control plane",
        previous_summaries=["Раздел про мотивацию и pain points."],
        include_code_examples=True,
    )

    assert "Уже написанные разделы" in prompt
    assert "pain points" in prompt


def test_conclusion_prompt_contains_summaries():
    prompt = build_conclusion_prompt(
        topic="Kubernetes",
        outline_markdown="# Title",
        section_summaries=["Итог первого раздела", "Итог второго раздела"],
    )

    assert "Итог первого раздела" in prompt
    assert "Напиши заключение" in prompt
