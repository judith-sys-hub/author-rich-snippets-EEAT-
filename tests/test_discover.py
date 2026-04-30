from pathlib import Path

FIXTURE = Path(__file__).parent / "fixtures" / "autor_list.html"


def test_parse_extracts_three_slugs():
    from scraper.discover import parse_autor_page
    authors = parse_autor_page(FIXTURE.read_text(encoding="utf-8"))
    assert len(authors) == 3
    slugs = [a["slug"] for a in authors]
    assert "maria-muster" in slugs
    assert "hans-beispiel" in slugs
    assert "anna-redakteurin" in slugs


def test_parse_extracts_names():
    from scraper.discover import parse_autor_page
    authors = parse_autor_page(FIXTURE.read_text(encoding="utf-8"))
    names = [a["name"] for a in authors]
    assert "Maria Muster" in names


def test_parse_builds_absolute_profile_url():
    from scraper.discover import parse_autor_page
    authors = parse_autor_page(FIXTURE.read_text(encoding="utf-8"))
    maria = next(a for a in authors if a["slug"] == "maria-muster")
    assert maria["profile_url"] == "https://www.kleinezeitung.at/autor/maria-muster"


def test_parse_skips_bare_autor_link():
    from scraper.discover import parse_autor_page
    html = ("<html><body>"
            "<a href='/autor/'>Alle Autoren</a>"
            "<a href='/autor/maria-muster'>Maria Muster</a>"
            "</body></html>")
    authors = parse_autor_page(html)
    assert len(authors) == 1
    assert authors[0]["slug"] == "maria-muster"


def test_parse_deduplicates_slugs():
    from scraper.discover import parse_autor_page
    html = ("<html><body>"
            "<a href='/autor/maria-muster'>Maria Muster</a>"
            "<a href='/autor/maria-muster'>Maria Muster (doppelt)</a>"
            "</body></html>")
    authors = parse_autor_page(html)
    assert len(authors) == 1
