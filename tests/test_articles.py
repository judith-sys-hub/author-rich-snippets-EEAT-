from pathlib import Path

FIXTURE = Path(__file__).parent / "fixtures" / "author_profile.html"


def test_extracts_name():
    from scraper.articles import parse_author_profile
    result = parse_author_profile(FIXTURE.read_text(encoding="utf-8"), "maria-muster")
    assert result["profile"]["name"] == "Maria Muster"


def test_extracts_title():
    from scraper.articles import parse_author_profile
    result = parse_author_profile(FIXTURE.read_text(encoding="utf-8"), "maria-muster")
    assert result["profile"]["title"] == "Redakteurin"


def test_extracts_bio():
    from scraper.articles import parse_author_profile
    result = parse_author_profile(FIXTURE.read_text(encoding="utf-8"), "maria-muster")
    assert "Maria Muster" in result["profile"]["bio_existing"]


def test_filters_articles_to_active_years():
    from scraper.articles import parse_author_profile
    result = parse_author_profile(FIXTURE.read_text(encoding="utf-8"), "maria-muster")
    # Fixture has 2 articles in 2025 and 1 in 2024 — only 2025 should be kept
    assert len(result["articles"]) == 2
    for article in result["articles"]:
        assert article["published_at"].startswith("2025")


def test_caps_at_15_articles():
    from scraper.articles import parse_author_profile
    articles_html = "".join(
        f"<article>"
        f"<a href='/artikel/{i}'>Artikel {i}</a>"
        f"<time datetime='2025-01-{(i % 28) + 1:02d}T00:00:00'>Tag</time>"
        f"<span class='article-ressort'>Politik</span>"
        f"</article>"
        for i in range(20)
    )
    html = (f"<html><body>"
            f"<h1 class='author-name'>Test Autor</h1>"
            f"<section class='author-articles'>{articles_html}</section>"
            f"</body></html>")
    result = parse_author_profile(html, "test-autor")
    assert len(result["articles"]) == 15


def test_returns_none_for_inactive_author():
    from scraper.articles import parse_author_profile
    html = ("<html><body>"
            "<h1 class='author-name'>Alter Autor</h1>"
            "<section class='author-articles'>"
            "<article>"
            "<a href='/artikel/1'>Artikel 2020</a>"
            "<time datetime='2020-06-01T00:00:00'>2020</time>"
            "<span class='article-ressort'>Politik</span>"
            "</article>"
            "</section></body></html>")
    assert parse_author_profile(html, "alter-autor") is None
