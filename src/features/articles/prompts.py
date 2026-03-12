def build_blog_system_prompt(target_audience: str, style: str) -> str:
    return (
        "Ты пишешь технические статьи. "
        f"Аудитория: {target_audience}. "
        f"Стиль: {style}. "
        "Без приветствий. Без фраз про помощь. Без лишних пояснений."
    )


def build_outline_prompt(
    topic: str,
    desired_sections_count: int,
    include_code_examples: bool,
) -> str:
    code_examples = "Добавь code examples там, где это полезно." if include_code_examples else "Code examples не обязательны."
    return (
        f'Тема: "{topic}".\n'
        f"Нужно {desired_sections_count} sections.\n"
        'Верни только JSON.\n'
        'Формат: {"title":"...","sections":[{"title":"...","description":"..."}]}.\n'
        "Без markdown. Без текста до JSON. Без текста после JSON.\n"
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
        "Добавь code examples, CLI или config если это полезно."
        if include_code_examples
        else "Code examples не обязательны."
    )
    return (
        f"Тема: {topic}\n\n"
        f"Outline:\n{outline_markdown}\n\n"
        f"{context_block}\n\n"
        f"Section title: {section_title}\n"
        f"Section goal: {section_description}\n\n"
        "Напиши только этот section.\n"
        "Без приветствия. Без вступления про помощь.\n"
        "Не повторяй предыдущие sections.\n"
        "Пиши конкретно и технически.\n"
        f"{code_requirement}\n"
    )


def build_summary_prompt(section_title: str, section_text: str) -> str:
    return (
        f"Сделай короткое summary section '{section_title}'.\n"
        "Нужно 3 предложения.\n"
        "Только факты и ключевые идеи.\n"
        "Без приветствия. Без фраз про помощь.\n\n"
        f"{section_text}"
    )


def build_conclusion_prompt(topic: str, outline_markdown: str, section_summaries: list[str]) -> str:
    joined_summaries = "\n".join(f"- {summary}" for summary in section_summaries)
    return (
        f"Тема: {topic}\n\n"
        f"Outline:\n{outline_markdown}\n\n"
        "Summary sections:\n"
        f"{joined_summaries}\n\n"
        "Напиши короткое conclusion.\n"
        "Собери главные выводы.\n"
        "Покажи практическую ценность.\n"
        "Без приветствия. Без мета-текста."
    )


def build_proofreading_prompt(title: str, article_markdown: str) -> str:
    return (
        f"Title: {title}\n\n"
        "Отредактируй текст.\n"
        "Исправь грамматику.\n"
        "Убери повторы.\n"
        "Убери приветствия и assistant-style фразы.\n"
        "Сохрани markdown-структуру.\n\n"
        f"{article_markdown}"
    )
