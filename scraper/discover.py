import os
import time

from bs4 import BeautifulSoup
from playwright.sync_api import BrowserContext

from scraper.state import upsert_author

BASE_URL = "https://www.kleinezeitung.at"
AUTOR_PATH = "/autor"


def parse_autor_page(html: str) -> list[dict]:
    """
    Parse /autor listing HTML and return author dicts.

    IMPORTANT: Run `python pipeline.py --dry-run --stage discover` against
    the live site and inspect logged HTML to verify these selectors are correct.
    Adjust if kleinezeitung.at uses different markup.
    """
    soup = BeautifulSoup(html, "lxml")
    authors: list[dict] = []
    seen: set[str] = set()

    for link in soup.select("a[href]"):
        href = link.get("href", "")
        parts = href.rstrip("/").split("/")
        # Match /autor/{slug} — requires exactly "autor" as second-to-last segment
        if len(parts) >= 2 and parts[-2] == "autor" and parts[-1]:
            slug = parts[-1]
            if slug in seen:
                continue
            seen.add(slug)
            name = link.get_text(strip=True)
            if name:
                authors.append({
                    "slug": slug,
                    "name": name,
                    "profile_url": f"{BASE_URL}/autor/{slug}",
                })
    return authors


def discover_authors(context: BrowserContext, dry_run: bool = False) -> list[dict]:
    delay = float(os.environ.get("SCRAPE_DELAY_SECONDS", "2"))
    page = context.new_page()
    page.goto(f"{BASE_URL}{AUTOR_PATH}")
    time.sleep(delay)
    authors = parse_autor_page(page.content())
    page.close()

    if not dry_run:
        for author in authors:
            upsert_author(author["slug"], author["name"])

    return authors
