import argparse
import json
import os
import sys
import time
from pathlib import Path

from dotenv import load_dotenv
from playwright.sync_api import sync_playwright

load_dotenv()

DATA_DIR = Path(__file__).parent / "data" / "authors"
DATA_DIR.mkdir(parents=True, exist_ok=True)


def run_discover(context, dry_run: bool, limit: int | None) -> None:
    from scraper.discover import discover_authors
    print("[discover] Suche Autoren auf /autor ...")
    authors = discover_authors(context, dry_run=dry_run)
    if limit:
        authors = authors[:limit]
    suffix = " (dry-run, keine Änderungen)" if dry_run else ""
    print(f"[discover] {len(authors)} Autoren gefunden{suffix}")


def run_scrape(context, dry_run: bool, limit: int | None) -> None:
    from scraper.articles import scrape_author
    from scraper.schema import validate_author
    from scraper.state import get_authors_for_scrape, update_stage

    candidates = list(get_authors_for_scrape())
    if limit:
        candidates = candidates[:limit]
    print(f"[scrape] Verarbeite {len(candidates)} Autoren ...")

    for row in candidates:
        slug = row["slug"]
        author_id = row["author_id"]
        profile_url = (
            f"https://www.kleinezeitung.at/autor/{author_id}/{slug}"
            if author_id else
            f"https://www.kleinezeitung.at/autor/{slug}"
        )
        if dry_run:
            print(f"[scrape] Würde scrapen: {slug}")
            continue
        try:
            data = scrape_author(context, slug, profile_url)
            if data is None:
                print(f"[scrape] Kein 2025/26-Artikel: {slug} → inactive")
                update_stage(slug, "inactive")
                continue
            validate_author(data)
            (DATA_DIR / f"{slug}.json").write_text(
                json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8"
            )
            update_stage(slug, "scraped")
            print(f"[scrape] OK: {slug}")
        except Exception as exc:
            update_stage(slug, "failed", error=str(exc))
            print(f"[scrape] FEHLER: {slug} — {exc}", file=sys.stderr)


def run_enrich(dry_run: bool, limit: int | None) -> None:
    from scraper.enrich import enrich_author
    from scraper.schema import validate_author
    from scraper.state import get_authors_by_stage, update_stage

    candidates = list(get_authors_by_stage("scraped"))
    if limit:
        candidates = candidates[:limit]
    print(f"[enrich] Verarbeite {len(candidates)} Autoren ...")

    for row in candidates:
        slug = row["slug"]
        out_path = DATA_DIR / f"{slug}.json"
        if dry_run:
            print(f"[enrich] Würde anreichern: {slug}")
            continue
        try:
            data = json.loads(out_path.read_text(encoding="utf-8"))
            data = enrich_author(data)
            validate_author(data)
            out_path.write_text(
                json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8"
            )
            update_stage(slug, "enriched")
            print(f"[enrich] OK: {slug}")
        except Exception as exc:
            update_stage(slug, "failed", error=str(exc))
            print(f"[enrich] FEHLER: {slug} — {exc}", file=sys.stderr)


def run_generate(dry_run: bool, limit: int | None) -> None:
    from scraper.generate import SYSTEM_PROMPT, generate_bio
    from scraper.state import get_authors_by_stage, update_stage

    candidates = list(get_authors_by_stage("enriched"))
    if limit:
        candidates = candidates[:limit]
    print(f"[generate] Verarbeite {len(candidates)} Autoren ...")

    if dry_run:
        for row in candidates:
            print(f"[generate] Würde generieren: {row['slug']}")
        return

    import anthropic
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        print("[generate] FEHLER: ANTHROPIC_API_KEY ist nicht gesetzt.", file=sys.stderr)
        sys.exit(1)
    client = anthropic.Anthropic(api_key=api_key)
    delay = float(os.environ.get("SCRAPE_DELAY_SECONDS", "2"))

    for row in candidates:
        slug = row["slug"]
        out_path = DATA_DIR / f"{slug}.json"
        try:
            data = json.loads(out_path.read_text(encoding="utf-8"))
            data = generate_bio(data, client, SYSTEM_PROMPT)
            out_path.write_text(
                json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8"
            )
            update_stage(slug, "generated")
            print(f"[generate] OK: {slug}")
        except Exception as exc:
            update_stage(slug, "failed", error=str(exc))
            print(f"[generate] FEHLER: {slug} — {exc}", file=sys.stderr)
        time.sleep(delay)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Kleine Zeitung Autorenprofil-Pipeline"
    )
    parser.add_argument("--dry-run", action="store_true",
                        help="Aktionen loggen ohne Dateien zu schreiben")
    parser.add_argument("--limit", type=int, default=None,
                        help="Nur N Autoren verarbeiten")
    parser.add_argument("--stage", choices=["discover", "scrape", "enrich", "generate"],
                        default=None, help="Nur eine Stage ausführen")
    args = parser.parse_args()

    from scraper.state import init_db
    init_db()

    needs_browser = args.stage in (None, "discover", "scrape")

    with sync_playwright() as playwright:
        context = None
        if needs_browser:
            from scraper.auth import get_authenticated_context
            context = get_authenticated_context(playwright)

        if args.stage in (None, "discover"):
            run_discover(context, args.dry_run, args.limit)
        if args.stage in (None, "scrape"):
            run_scrape(context, args.dry_run, args.limit)
        if args.stage in (None, "enrich"):
            run_enrich(args.dry_run, args.limit)
        if args.stage in (None, "generate"):
            run_generate(args.dry_run, args.limit)


if __name__ == "__main__":
    main()
