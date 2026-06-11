"""Checks which linked Instagram / X author profiles are private.

Requires a logged-in session created by login_social.py.

Output:
  socialcheck/social_private_report.xlsx  - all checked profiles with status
  socialcheck/social_private_report.md    - markdown summary (private only on top)

Status values:
  private    - account requires a follow/friend request
  public     - account is publicly visible
  not_found  - profile no longer exists (404 / suspended)
  error      - check failed (see notes column)
"""

import glob
import json
import re
import sys
import time
from pathlib import Path

from openpyxl import Workbook
from playwright.sync_api import sync_playwright

BASE = Path(__file__).parent.parent
PROFILE_DIR = Path(__file__).parent / ".browser_profile"
XLSX_PATH = Path(__file__).parent / "social_private_report.xlsx"
MD_PATH = Path(__file__).parent / "social_private_report.md"

DELAY_SECONDS = 6  # polite delay between profile visits


def extract_handle(url: str, platform: str) -> str | None:
    pattern = {
        "instagram": r"instagram\.com/([A-Za-z0-9_.]+)",
        "twitter": r"(?:twitter|x)\.com/([A-Za-z0-9_]+)",
    }[platform]
    m = re.search(pattern, url)
    if not m:
        return None
    handle = m.group(1)
    if handle.lower() in {"p", "accounts", "explore", "i", "home", "search", "intent", "hashtag"}:
        return None
    return handle


def load_targets() -> list[dict]:
    targets = []
    for f in sorted(glob.glob(str(BASE / "data" / "authors" / "*.json"))):
        d = json.load(open(f, encoding="utf-8"))
        links = d.get("enrichment", {}).get("social_links", {}) or {}
        for platform in ("instagram", "twitter"):
            url = links.get(platform)
            if not url:
                continue
            handle = extract_handle(url, platform)
            if not handle:
                continue
            targets.append(
                {
                    "name": d["profile"]["name"],
                    "slug": d["meta"]["slug"],
                    "platform": "x" if platform == "twitter" else platform,
                    "handle": handle,
                    "url": url,
                }
            )
    return targets


def check_instagram(page, handle: str) -> tuple[str, str]:
    """Uses Instagram's own web API from a logged-in page context (reliable JSON)."""
    page.goto("https://www.instagram.com/", wait_until="domcontentloaded")
    result = page.evaluate(
        """async (handle) => {
            const r = await fetch(
                `https://www.instagram.com/api/v1/users/web_profile_info/?username=${handle}`,
                { headers: { 'x-ig-app-id': '936619743392459' } }
            );
            if (r.status === 404) return { status: 'not_found' };
            if (!r.ok) return { status: 'error', note: 'HTTP ' + r.status };
            const j = await r.json();
            const u = j?.data?.user;
            if (!u) return { status: 'not_found' };
            return { status: u.is_private ? 'private' : 'public',
                     note: `follower: ${u.edge_followed_by?.count ?? '?'}` };
        }""",
        handle,
    )
    return result["status"], result.get("note", "")


def check_x(page, handle: str) -> tuple[str, str]:
    """Visits the profile page logged-in and reads the rendered state."""
    page.goto(f"https://x.com/{handle}", wait_until="domcontentloaded")
    page.wait_for_timeout(6000)
    body = page.inner_text("body")
    low = body.lower()
    if "diese posts sind geschützt" in low or "these posts are protected" in low:
        return "private", ""
    if "dieses konto existiert nicht" in low or "this account doesn" in low:
        return "not_found", ""
    if "konto gesperrt" in low or "account suspended" in low:
        return "not_found", "suspended"
    if "follower" in low or "following" in low or "folge ich" in low:
        return "public", ""
    return "error", "Seite nicht eindeutig erkannt"


def main() -> None:
    if not PROFILE_DIR.exists():
        sys.exit("Kein Browser-Profil gefunden - bitte zuerst login_social.py ausfuehren.")

    targets = load_targets()
    print(f"{len(targets)} Profile zu pruefen "
          f"({sum(t['platform'] == 'instagram' for t in targets)} Instagram, "
          f"{sum(t['platform'] == 'x' for t in targets)} X)")

    results = []
    with sync_playwright() as p:
        # same real-Chrome profile as login_social.py; visible window to avoid
        # headless bot detection - just leave it in the background
        context = p.chromium.launch_persistent_context(
            str(PROFILE_DIR),
            channel="chrome",
            headless=False,
            locale="de-AT",
            args=["--disable-blink-features=AutomationControlled", "--window-position=2000,50"],
            ignore_default_args=["--enable-automation"],
        )
        page = context.new_page()

        for i, t in enumerate(targets, 1):
            try:
                if t["platform"] == "instagram":
                    status, note = check_instagram(page, t["handle"])
                else:
                    status, note = check_x(page, t["handle"])
            except Exception as e:  # noqa: BLE001 - record and continue
                status, note = "error", str(e)[:120]
            results.append({**t, "status": status, "note": note})
            print(f"[{i}/{len(targets)}] {t['platform']:9} @{t['handle']:25} -> {status} {note}")
            time.sleep(DELAY_SECONDS)

        context.close()

    write_xlsx(results)
    write_md(results)
    private = [r for r in results if r["status"] == "private"]
    print(f"\nFertig. {len(private)} private Profile gefunden.")
    print(f"Report: {XLSX_PATH}")


def write_xlsx(results: list[dict]) -> None:
    wb = Workbook()
    ws = wb.active
    ws.title = "Social Privacy Check"
    ws.append(["Autor", "Slug", "Plattform", "Handle", "Profil-URL", "Status", "Notiz"])
    order = {"private": 0, "error": 1, "not_found": 2, "public": 3}
    for r in sorted(results, key=lambda r: (order.get(r["status"], 9), r["name"])):
        ws.append([r["name"], r["slug"], r["platform"], r["handle"], r["url"], r["status"], r["note"]])
    wb.save(XLSX_PATH)


def write_md(results: list[dict]) -> None:
    private = [r for r in results if r["status"] == "private"]
    other = [r for r in results if r["status"] != "private"]
    lines = ["# Social Privacy Check\n", f"\n## Private Profile ({len(private)})\n",
             "\n| Autor | Plattform | Profil |\n|---|---|---|\n"]
    for r in sorted(private, key=lambda r: r["name"]):
        lines.append(f"| {r['name']} | {r['platform']} | {r['url']} |\n")
    lines.append(f"\n## Alle weiteren geprueften Profile ({len(other)})\n")
    lines.append("\n| Autor | Plattform | Profil | Status | Notiz |\n|---|---|---|---|---|\n")
    for r in sorted(other, key=lambda r: (r["status"], r["name"])):
        lines.append(f"| {r['name']} | {r['platform']} | {r['url']} | {r['status']} | {r['note']} |\n")
    MD_PATH.write_text("".join(lines), encoding="utf-8")


if __name__ == "__main__":
    main()
