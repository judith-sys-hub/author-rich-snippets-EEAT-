import pytest


@pytest.fixture
def tmp_db(tmp_path, monkeypatch):
    import scraper.state as state_mod
    monkeypatch.setattr(state_mod, "DB_PATH", tmp_path / "test.db")
    yield tmp_path / "test.db"


def test_init_db_creates_authors_table(tmp_db):
    from scraper.state import init_db, get_connection
    init_db()
    with get_connection() as conn:
        tables = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()
    assert any(t["name"] == "authors" for t in tables)


def test_upsert_author_inserts_new(tmp_db):
    from scraper.state import init_db, upsert_author, get_connection
    init_db()
    upsert_author("maria-muster", "Maria Muster")
    with get_connection() as conn:
        row = conn.execute(
            "SELECT * FROM authors WHERE slug = ?", ("maria-muster",)
        ).fetchone()
    assert row["slug"] == "maria-muster"
    assert row["name"] == "Maria Muster"
    assert row["stage"] == "discovered"


def test_upsert_author_does_not_overwrite_existing(tmp_db):
    from scraper.state import init_db, upsert_author, update_stage, get_connection
    init_db()
    upsert_author("maria-muster", "Maria Muster")
    update_stage("maria-muster", "scraped")
    upsert_author("maria-muster", "Maria Muster")  # re-insert must not reset stage
    with get_connection() as conn:
        row = conn.execute(
            "SELECT * FROM authors WHERE slug = ?", ("maria-muster",)
        ).fetchone()
    assert row["stage"] == "scraped"


def test_update_stage_sets_last_scraped(tmp_db):
    from scraper.state import init_db, upsert_author, update_stage, get_connection
    init_db()
    upsert_author("maria-muster", "Maria Muster")
    update_stage("maria-muster", "enriched")
    with get_connection() as conn:
        row = conn.execute(
            "SELECT * FROM authors WHERE slug = ?", ("maria-muster",)
        ).fetchone()
    assert row["stage"] == "enriched"
    assert row["last_scraped"] is not None


def test_update_stage_records_error(tmp_db):
    from scraper.state import init_db, upsert_author, update_stage, get_connection
    init_db()
    upsert_author("maria-muster", "Maria Muster")
    update_stage("maria-muster", "failed", error="Connection timeout")
    with get_connection() as conn:
        row = conn.execute(
            "SELECT * FROM authors WHERE slug = ?", ("maria-muster",)
        ).fetchone()
    assert row["stage"] == "failed"
    assert row["error"] == "Connection timeout"


def test_get_authors_by_stage(tmp_db):
    from scraper.state import init_db, upsert_author, update_stage, get_authors_by_stage
    init_db()
    upsert_author("author-a", "Author A")
    upsert_author("author-b", "Author B")
    update_stage("author-b", "scraped")
    discovered = get_authors_by_stage("discovered")
    assert len(discovered) == 1
    assert discovered[0]["slug"] == "author-a"


def test_get_authors_for_scrape_returns_discovered(tmp_db):
    from scraper.state import init_db, upsert_author, get_authors_for_scrape
    init_db()
    upsert_author("fresh-author", "Fresh Author")
    result = get_authors_for_scrape()
    slugs = [r["slug"] for r in result]
    assert "fresh-author" in slugs
