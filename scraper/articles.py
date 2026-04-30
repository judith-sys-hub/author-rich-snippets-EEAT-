import os
import time
from datetime import datetime, timezone

from bs4 import BeautifulSoup, Tag
from playwright.sync_api import BrowserContext

from scraper.schema import empty_author

BASE_URL = "https://www.kleinezeitung.at"
ACTIVE_YEARS = {2025, 2026}
MAX_ARTICLES = 15


def _text(el: Tag | None, selector: str | None = None) -> str | None:
    if selector:
        el = el.select_one(selector) if el else None
    return el.get_text(strip=True) if el else None


def parse_author_profile(html: str, slug: str) -> dict | None:
    """
    Parse author profile page HTML into an author dict.
    Returns None when the author has no articles in ACTIVE_YEARS.

    IMPORTANT: CSS selectors are based on fixture HTML. Run
    `python pipeline.py --dry-run --stage scrape` and inspect page.content()
    output to verify selectors against the live site. Adjust as needed.
    """
    soup = BeautifulSoup(html, "lxml")
    name = _text(soup, "h1.author-name") or slug
    profile_url = f"{BASE_URL}/autor/{slug}"

    author = empty_author(slug, name, profile_url)
    author["profile"]["title"] = _text(soup, ".author-job-title")
    author["profile"]["department"] = _text(soup, ".author-department")
    author["profile"]["bio_existing"] = _text(soup, ".author-bio-text")
    img = soup.select_one(".author-avatar")
    if img:
        author["profile"]["photo_url"] = img.get("src")

    articles: list[dict] = []
    for el in soup.select("section.author-articles article"):
        link = el.select_one("a[href]")
        time_el = el.select_one("time[datetime]")
        if not link or not time_el:
            continue
        raw_dt = time_el.get("datetime", "")
        try:
            year = int(raw_dt[:4])
        except (ValueError, IndexError):
            continue
        if year not in ACTIVE_YEARS:
            continue
        articles.append({
            "url": BASE_URL + link.get("href", ""),
            "title": link.get_text(strip=True),
            "published_at": raw_dt[:10],
            "section": _text(el, ".article-ressort"),
            "word_count": None,
        })

    if not articles:
        return None

    author["articles"] = articles[:MAX_ARTICLES]
    author["meta"]["last_scraped"] = datetime.now(timezone.utc).isoformat()
    return author


def scrape_author(context: BrowserContext, slug: str, profile_url: str) -> dict | None:
    delay = float(os.environ.get("SCRAPE_DELAY_SECONDS", "2"))
    page = context.new_page()
    page.goto(profile_url)
    time.sleep(delay)
    result = parse_author_profile(page.content(), slug)
    page.close()
    return result
