import pytest
from scraper.schema import empty_author


def _author():
    return empty_author("maria-muster", "Maria Muster",
                        "https://www.kleinezeitung.at/autor/maria-muster")


def test_adds_wikipedia_url(monkeypatch):
    import scraper.enrich as mod
    monkeypatch.setattr(mod, "fetch_wikipedia",
                        lambda name: {"url": "https://de.wikipedia.org/wiki/Maria_Muster"})
    monkeypatch.setattr(mod, "search_duckduckgo", lambda q: [])
    result = mod.enrich_author(_author(), delay=0)
    assert result["enrichment"]["wikipedia_url"] == "https://de.wikipedia.org/wiki/Maria_Muster"
    assert "wikipedia.org/de" in result["enrichment"]["enrichment_sources"]


def test_adds_awards_from_horizont(monkeypatch):
    import scraper.enrich as mod
    monkeypatch.setattr(mod, "fetch_wikipedia", lambda n: None)
    def mock_ddg(query):
        if "horizont.at" in query:
            return [{"title": "Journalistin des Jahres",
                     "url": "https://horizont.at/award", "snippet": ""}]
        return []
    monkeypatch.setattr(mod, "search_duckduckgo", mock_ddg)
    result = mod.enrich_author(_author(), delay=0)
    assert any(a["source_url"] == "https://horizont.at/award"
               for a in result["enrichment"]["awards"])
    assert all(not a["verified"] for a in result["enrichment"]["awards"])


def test_preserves_verified_awards(monkeypatch):
    import scraper.enrich as mod
    monkeypatch.setattr(mod, "fetch_wikipedia", lambda n: None)
    monkeypatch.setattr(mod, "search_duckduckgo", lambda q: [])
    author = _author()
    author["enrichment"]["awards"] = [
        {"title": "Verifizierter Preis", "year": 2023,
         "source_url": "https://example.com", "verified": True}
    ]
    result = mod.enrich_author(author, delay=0)
    verified = [a for a in result["enrichment"]["awards"] if a["verified"]]
    assert len(verified) == 1
    assert verified[0]["title"] == "Verifizierter Preis"


def test_adds_linkedin_social_link(monkeypatch):
    import scraper.enrich as mod
    monkeypatch.setattr(mod, "fetch_wikipedia", lambda n: None)
    def mock_ddg(query):
        if "linkedin.com" in query:
            return [{"title": "Maria Muster | LinkedIn",
                     "url": "https://linkedin.com/in/maria-muster", "snippet": ""}]
        return []
    monkeypatch.setattr(mod, "search_duckduckgo", mock_ddg)
    result = mod.enrich_author(_author(), delay=0)
    assert result["enrichment"]["social_links"]["linkedin"] == \
        "https://linkedin.com/in/maria-muster"
