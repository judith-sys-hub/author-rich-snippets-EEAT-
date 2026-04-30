import time

import httpx
from bs4 import BeautifulSoup


def fetch_wikipedia(name: str) -> dict | None:
    slug = name.replace(" ", "_")
    url = f"https://de.wikipedia.org/api/rest_v1/page/summary/{slug}"
    try:
        resp = httpx.get(url, timeout=10, follow_redirects=True)
        if resp.status_code == 200:
            data = resp.json()
            page_url = (data.get("content_urls", {})
                            .get("desktop", {})
                            .get("page"))
            return {"url": page_url} if page_url else None
    except httpx.HTTPError:
        pass
    return None


def search_duckduckgo(query: str) -> list[dict]:
    try:
        resp = httpx.post(
            "https://html.duckduckgo.com/html/",
            data={"q": query},
            headers={"User-Agent": "Mozilla/5.0 (compatible; klz-research/1.0)"},
            timeout=15,
            follow_redirects=True,
        )
        soup = BeautifulSoup(resp.text, "lxml")
        results = []
        for el in soup.select(".result"):
            title_el = el.select_one(".result__title a")
            snippet_el = el.select_one(".result__snippet")
            if title_el:
                results.append({
                    "title": title_el.get_text(strip=True),
                    "url": title_el.get("href", ""),
                    "snippet": snippet_el.get_text(strip=True) if snippet_el else "",
                })
        return results[:5]
    except httpx.HTTPError:
        return []


def enrich_author(author_data: dict, delay: float = 3.0) -> dict:
    name = author_data["profile"]["name"]
    enrichment = author_data.setdefault("enrichment", {})
    existing_verified = [a for a in enrichment.get("awards", []) if a.get("verified")]
    new_awards: list[dict] = []
    sources: list[str] = []

    # Wikipedia
    wiki = fetch_wikipedia(name)
    if wiki:
        enrichment["wikipedia_url"] = wiki["url"]
        sources.append("wikipedia.org/de")
    time.sleep(delay)

    # Horizont
    horizont = search_duckduckgo(f'"{name}" site:horizont.at')
    if horizont:
        new_awards += [{"title": r["title"], "year": None,
                        "source_url": r["url"], "verified": False}
                       for r in horizont]
        sources.append("horizont.at")
    time.sleep(delay)

    # derStandard Etat
    standard = search_duckduckgo(f'"{name}" site:derstandard.at/etat')
    if standard:
        new_awards += [{"title": r["title"], "year": None,
                        "source_url": r["url"], "verified": False}
                       for r in standard]
        sources.append("derstandard.at")
    time.sleep(delay)

    # Social links
    social = enrichment.get("social_links", {
        "linkedin": None, "bluesky": None, "twitter": None, "instagram": None
    })
    for platform, domain in [
        ("linkedin", "linkedin.com/in"),
        ("bluesky", "bsky.app"),
        ("twitter", "twitter.com"),
        ("instagram", "instagram.com"),
    ]:
        hits = search_duckduckgo(f'"{name}" kleinezeitung site:{domain}')
        if hits:
            social[platform] = hits[0]["url"]
        time.sleep(delay)

    enrichment["awards"] = existing_verified + new_awards
    enrichment["social_links"] = social
    enrichment["enrichment_sources"] = list(set(sources))
    author_data["enrichment"] = enrichment
    return author_data
