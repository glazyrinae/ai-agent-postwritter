def build_blog_system_prompt(target_audience: str, style: str) -> str:
    return (
        "Ты опытный технический автор IT-блога. "
        f"Целевая аудитория: {target_audience}. "
        f"Желаемый стиль: {style}. "
        "Пиши структурированно, без воды, с фокусом на практику, архитектурные решения и инженерные trade-off."
    )


def build_outline_prompt(
    topic: str,
    desired_sections_count: int,
    include_code_examples: bool,
) -> str:
    code_examples = "Да, укажи где уместны примеры кода." if include_code_examples else "Нет, не делай акцент на коде."
    return (
        f'Составь подробный outline статьи для IT-блога на тему "{topic}".\n'
        f"Нужно ровно {desired_sections_count} основных разделов.\n"
        "Первая строка должна быть markdown-заголовком вида `# Название статьи`.\n"
        "Далее выдай нумерованный список, где каждая строка строго в формате:\n"
        "`1. Название раздела :: краткое описание раздела`.\n"
        "Не добавляй заключение в список, оно будет сгенерировано отдельно.\n"
        f"{code_examples}"
    )


def build_section_prompt(
    topic: str,
    outline_markdown: str,
    section_title: str,
    section_description: str,
    previous_summaries: list[str],
    include_code_examples: bool,
) -> str:
    context_block = "Пока это первая глава статьи."
    if previous_summaries:
        context_lines = "\n".join(
            f"- {summary.strip()}" for summary in previous_summaries if summary.strip()
        )
        context_block = f"Уже написанные разделы в кратком виде:\n{context_lines}"

    code_requirement = (
        "Добавь примеры кода, CLI-команды или конфигурации там, где это уместно."
        if include_code_examples
        else "Примеры кода не обязательны."
    )
    return (
        f"Тема статьи: {topic}\n\n"
        f"Общий outline статьи:\n{outline_markdown}\n\n"
        f"{context_block}\n\n"
        f"Напиши следующий раздел.\n"
        f"Название раздела: {section_title}\n"
        f"О чем раздел: {section_description}\n\n"
        "Требования:\n"
        "- Пиши как для сильного технического блога.\n"
        "- Не повторяй уже описанные идеи.\n"
        "- Давай практические примеры, инженерные детали и ограничения подходов.\n"
        f"- {code_requirement}\n"
        "- Используй подзаголовки и списки, если это усиливает читаемость.\n"
        "- Избегай общих фраз и маркетинговой воды.\n"
    )


def build_summary_prompt(section_title: str, section_text: str) -> str:
    return (
        f"Сделай краткое резюме раздела '{section_title}' для использования как контекст при генерации следующей главы.\n"
        "Нужно 3-5 предложений, только ключевые идеи, без украшений.\n\n"
        f"{section_text}"
    )


def build_conclusion_prompt(topic: str, outline_markdown: str, section_summaries: list[str]) -> str:
    joined_summaries = "\n".join(f"- {summary}" for summary in section_summaries)
    return (
        f"Тема статьи: {topic}\n\n"
        f"Outline статьи:\n{outline_markdown}\n\n"
        "Ниже краткие summary уже написанных разделов:\n"
        f"{joined_summaries}\n\n"
        "Напиши заключение для статьи IT-блога. "
        "Оно должно коротко собрать главные выводы, показать практическую ценность и дать читателю направление для следующего шага."
    )
