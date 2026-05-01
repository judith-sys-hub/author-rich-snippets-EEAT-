import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).parent.parent / "pipeline.db"


def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    with get_connection() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS authors (
                slug        TEXT PRIMARY KEY,
                author_id   TEXT,
                name        TEXT,
                stage       TEXT DEFAULT 'discovered',
                last_scraped TEXT,
                error       TEXT
            )
        """)
        # migration: add author_id to existing databases
        try:
            conn.execute("ALTER TABLE authors ADD COLUMN author_id TEXT")
        except Exception:
            pass


def upsert_author(slug: str, name: str, author_id: str | None = None) -> None:
    with get_connection() as conn:
        conn.execute(
            "INSERT INTO authors (slug, author_id, name, stage) VALUES (?, ?, ?, 'discovered') "
            "ON CONFLICT(slug) DO NOTHING",
            (slug, author_id, name),
        )


def update_stage(slug: str, stage: str, error: str | None = None) -> None:
    with get_connection() as conn:
        conn.execute(
            "UPDATE authors SET stage = ?, error = ?, last_scraped = datetime('now') "
            "WHERE slug = ?",
            (stage, error, slug),
        )


def get_authors_by_stage(stage: str) -> list[sqlite3.Row]:
    with get_connection() as conn:
        return conn.execute(
            "SELECT * FROM authors WHERE stage = ?", (stage,)
        ).fetchall()


def get_authors_for_scrape(days: int = 7) -> list[sqlite3.Row]:
    with get_connection() as conn:
        return conn.execute(
            """
            SELECT * FROM authors
            WHERE stage = 'discovered'
               OR (stage IN ('scraped', 'enriched')
                   AND (last_scraped IS NULL
                        OR datetime(last_scraped) < datetime('now', ?)))
            """,
            (f"-{days} days",),
        ).fetchall()
