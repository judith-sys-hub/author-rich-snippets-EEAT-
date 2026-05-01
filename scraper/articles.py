import os
import re
import time
from datetime import datetime, timezone

from bs4 import BeautifulSoup, Tag
from playwright.sync_api import BrowserContext

from scraper.schema import empty_author

BASE_URL = "https://www.kleinezeitung.at"
ACTIVE_YEARS = {2025, 2026}
MAX_ARTICLES = 15

_ISO_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}")

_SOCIAL_DOMAIN_MAP = {
    "instagram.com": "instagram",
    "twitter.com":   "twitter",
    "x.com":         "twitter",
    "linkedin.com":  "linkedin",
    "bsky.app":      "bluesky",
}


def _text(el: Tag | None, selector: str | None = None) -> str | None:
    if selector:
        el = el.select_one(selector) if el else None
    return el.get_text(strip=True) if el else None


def _bio(soup: BeautifulSoup) -> str | None:
    # bio paragraph sits near the job-title element
    title_el = soup.select_one("h2.t-head-l-light")
    if title_el:
        for p in (title_el.parent or title_el).find_all("p", recursive=False):
            text = p.get_text(strip=True)
            if text:
                return text
    # fallback: first substantial paragraph outside nav/footer/header
    for p in soup.select("p"):
        if p.find_parent(["nav", "footer", "header"]):
            continue
        text = p.get_text(strip=True)
        if len(text) > 50:
            return text
    return None


def _social_links(soup: BeautifulSoup) -> dict:
    links: dict = {}
    for a in soup.select("a[href][rel='nofollow']"):
        href = a.get("href", "")
        for domain, key in _SOCIAL_DOMAIN_MAP.items():
            if domain in href and key not in links:
                links[key] = href
    return links


def parse_author_profile(html: str, slug: str, profile_url: str) -> dict | None:
    soup = BeautifulSoup(html, "lxml")

    name = _text(soup, "h1.t-head-l") or slug
    author = empty_author(slug, name, profile_url)
    author["profile"]["title"] = _text(soup, "h2.t-head-l-light")
    author["profile"]["bio_existing"] = _bio(soup)

    img = soup.select_one("img.object-cover.rounded-full")
    if img:
        author["profile"]["photo_url"] = img.get("src")

    social = _social_links(soup)
    author["enrichment"]["social_links"].update(social)

    articles: list[dict] = []
    for el in soup.select("article[data-content-id]"):
        raw_dt = ""
        for div in el.select("div[title]"):
            val = div.get("title", "")
            if _ISO_DATE_RE.match(val):
                raw_dt = val
                break
        if not raw_dt:
            continue
        try:
            year = int(raw_dt[:4])
        except (ValueError, IndexError):
            continue
        if year not in ACTIVE_YEARS:
            continue

        link = el.select_one("a[href*='/artikel/']") or el.select_one("a[href]")
        if not link:
            continue

        href = link.get("href", "")
        articles.append({
            "url": href if href.startswith("http") else BASE_URL + href,
            "title": el.get("data-content-title") or link.get_text(strip=True),
            "published_at": raw_dt[:10],
            "section": el.get("data-content-kicker"),
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
    page.wait_for_load_state("networkidle")
    time.sleep(delay)
    result = parse_author_profile(page.content(), slug, profile_url)
    page.close()
    return result
