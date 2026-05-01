import os
import re
import time

from bs4 import BeautifulSoup
from playwright.sync_api import BrowserContext

from scraper.state import upsert_author

BASE_URL = "https://www.kleinezeitung.at"
AUTOR_PATH = "/autor"

# URL pattern: /autor/{numeric-id}/{slug}
_AUTOR_RE = re.compile(r"/autor/(\d+)/([^/?#]+)")


def parse_autor_page(html: str) -> list[dict]:
    soup = BeautifulSoup(html, "lxml")
    authors: list[dict] = []
    seen: set[str] = set()

    for link in soup.select("a[href]"):
        href = link.get("href", "")
        m = _AUTOR_RE.search(href)
        if not m:
            continue
        author_id, slug = m.group(1), m.group(2)
        if slug in seen:
            continue
        seen.add(slug)
        name = link.get_text(strip=True)
        if name:
            authors.append({
                "slug": slug,
                "author_id": author_id,
                "name": name,
                "profile_url": f"{BASE_URL}/autor/{author_id}/{slug}",
            })
    return authors


def discover_authors(context: BrowserContext, dry_run: bool = False) -> list[dict]:
    delay = float(os.environ.get("SCRAPE_DELAY_SECONDS", "2"))
    page = context.new_page()
    page.goto(f"{BASE_URL}{AUTOR_PATH}")
    page.wait_for_load_state("networkidle")
    time.sleep(delay)
    authors = parse_autor_page(page.content())
    page.close()

    if not dry_run:
        for author in authors:
            upsert_author(author["slug"], author["name"], author["author_id"])

    return authors
