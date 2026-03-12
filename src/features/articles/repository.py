from __future__ import annotations

import uuid
from typing import Any

import psycopg
from psycopg.rows import dict_row

from src.core.errors import PersistenceError, ResourceNotFoundError


RUN_STATUS_QUEUED = "queued"
RUN_STATUS_IN_PROGRESS = "in_progress"
RUN_STATUS_COMPLETED = "completed"
RUN_STATUS_FAILED = "failed"
RUN_STATUS_CANCELLED = "cancelled"

SECTION_STATUS_PENDING = "pending"
SECTION_STATUS_CONTENT_READY = "content_ready"
SECTION_STATUS_SUMMARY_READY = "summary_ready"
SECTION_STATUS_FAILED = "failed"


class ArticleRunRepository:
    def __init__(self, database_url: str):
        self.database_url = database_url.strip()
        self._schema_ready = False

    def ensure_schema(self) -> None:
        with self._connection() as conn:
            conn.close()

    def create_run(
        self,
        *,
        topic: str,
        target_audience: str,
        style: str,
        desired_sections_count: int,
        include_code_examples: bool,
        chapter_max_tokens: int,
    ) -> str:
        run_id = str(uuid.uuid4())
        with self._connection() as conn, conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO article_runs (
                    id,
                    status,
                    topic,
                    target_audience,
                    style,
                    desired_sections_count,
                    include_code_examples,
                    chapter_max_tokens,
                    current_step
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    run_id,
                    RUN_STATUS_IN_PROGRESS,
                    topic,
                    target_audience,
                    style,
                    desired_sections_count,
                    include_code_examples,
                    chapter_max_tokens,
                    "created",
                ),
            )
            conn.commit()
        return run_id

    def save_outline(self, run_id: str, title: str, outline_markdown: str, sections: list[dict[str, Any]]) -> None:
        with self._connection() as conn, conn.cursor() as cur:
            cur.execute(
                """
                UPDATE article_runs
                SET title = %s,
                    outline_markdown = %s,
                    current_step = %s,
                    updated_at = NOW()
                WHERE id = %s
                """,
                (title, outline_markdown, "outline_saved", run_id),
            )
            cur.execute("DELETE FROM article_run_sections WHERE run_id = %s", (run_id,))
            for section in sections:
                cur.execute(
                    """
                    INSERT INTO article_run_sections (
                        run_id,
                        section_index,
                        title,
                        description,
                        status
                    )
                    VALUES (%s, %s, %s, %s, %s)
                    """,
                    (
                        run_id,
                        section["index"],
                        section["title"],
                        section["description"],
                        SECTION_STATUS_PENDING,
                    ),
                )
            conn.commit()

    def save_section_content(self, run_id: str, section_index: int, content: str) -> None:
        with self._connection() as conn, conn.cursor() as cur:
            cur.execute(
                """
                UPDATE article_run_sections
                SET content = %s,
                    status = %s,
                    updated_at = NOW()
                WHERE run_id = %s AND section_index = %s
                """,
                (content, SECTION_STATUS_CONTENT_READY, run_id, section_index),
            )
            cur.execute(
                """
                UPDATE article_runs
                SET current_step = %s,
                    updated_at = NOW()
                WHERE id = %s
                """,
                (f"section_{section_index}_content_saved", run_id),
            )
            conn.commit()

    def save_section_summary(self, run_id: str, section_index: int, summary: str) -> None:
        with self._connection() as conn, conn.cursor() as cur:
            cur.execute(
                """
                UPDATE article_run_sections
                SET summary = %s,
                    status = %s,
                    updated_at = NOW()
                WHERE run_id = %s AND section_index = %s
                """,
                (summary, SECTION_STATUS_SUMMARY_READY, run_id, section_index),
            )
            cur.execute(
                """
                UPDATE article_runs
                SET current_step = %s,
                    updated_at = NOW()
                WHERE id = %s
                """,
                (f"section_{section_index}_summary_saved", run_id),
            )
            conn.commit()

    def save_conclusion(self, run_id: str, conclusion: str) -> None:
        with self._connection() as conn, conn.cursor() as cur:
            cur.execute(
                """
                UPDATE article_runs
                SET conclusion = %s,
                    current_step = %s,
                    updated_at = NOW()
                WHERE id = %s
                """,
                (conclusion, "conclusion_saved", run_id),
            )
            conn.commit()

    def complete_run(self, run_id: str, article_markdown: str) -> None:
        with self._connection() as conn, conn.cursor() as cur:
            cur.execute(
                """
                UPDATE article_runs
                SET article_markdown = %s,
                    status = %s,
                    current_step = %s,
                    finished_at = NOW(),
                    updated_at = NOW()
                WHERE id = %s
                """,
                (article_markdown, RUN_STATUS_COMPLETED, "completed", run_id),
            )
            conn.commit()

    def fail_run(self, run_id: str, current_step: str, error_message: str) -> None:
        with self._connection() as conn, conn.cursor() as cur:
            cur.execute(
                """
                UPDATE article_runs
                SET status = %s,
                    current_step = %s,
                    last_error = %s,
                    finished_at = NOW(),
                    updated_at = NOW()
                WHERE id = %s
                """,
                (RUN_STATUS_FAILED, current_step, error_message, run_id),
            )
            conn.commit()

    def get_run(self, run_id: str) -> dict[str, Any]:
        with self._connection() as conn, conn.cursor(row_factory=dict_row) as cur:
            cur.execute("SELECT * FROM article_runs WHERE id = %s", (run_id,))
            run = cur.fetchone()
            if not run:
                raise ResourceNotFoundError(f"Article run '{run_id}' was not found.")
            cur.execute(
                """
                SELECT section_index, title, description, status, content, summary
                FROM article_run_sections
                WHERE run_id = %s
                ORDER BY section_index
                """,
                (run_id,),
            )
            run["sections"] = cur.fetchall()
            return run

    def _connection(self) -> psycopg.Connection:
        if not self.database_url:
            raise PersistenceError("DATABASE_URL must not be empty.")
        try:
            conn = psycopg.connect(self.database_url)
        except Exception as exc:
            raise PersistenceError("Failed to connect to PostgreSQL.", details={"reason": str(exc)}) from exc
        if not self._schema_ready:
            try:
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        CREATE TABLE IF NOT EXISTS article_runs (
                            id TEXT PRIMARY KEY,
                            status TEXT NOT NULL,
                            topic TEXT NOT NULL,
                            target_audience TEXT NOT NULL,
                            style TEXT NOT NULL,
                            desired_sections_count INTEGER NOT NULL,
                            include_code_examples BOOLEAN NOT NULL,
                            chapter_max_tokens INTEGER NOT NULL,
                            title TEXT,
                            current_step TEXT,
                            outline_markdown TEXT,
                            conclusion TEXT,
                            article_markdown TEXT,
                            last_error TEXT,
                            started_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                            finished_at TIMESTAMPTZ,
                            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                            updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                        )
                        """
                    )
                    cur.execute(
                        """
                        CREATE TABLE IF NOT EXISTS article_run_sections (
                            id BIGSERIAL PRIMARY KEY,
                            run_id TEXT NOT NULL REFERENCES article_runs(id) ON DELETE CASCADE,
                            section_index INTEGER NOT NULL,
                            title TEXT NOT NULL,
                            description TEXT NOT NULL,
                            status TEXT NOT NULL,
                            content TEXT,
                            summary TEXT,
                            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                            updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                            UNIQUE(run_id, section_index)
                        )
                        """
                    )
                    conn.commit()
            except Exception as exc:
                conn.close()
                raise PersistenceError("Failed to initialize PostgreSQL schema.", details={"reason": str(exc)}) from exc
            self._schema_ready = True
        return conn
