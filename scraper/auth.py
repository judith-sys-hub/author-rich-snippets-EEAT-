import json
import os
from pathlib import Path

from playwright.sync_api import BrowserContext, Playwright

SESSION_PATH = Path(__file__).parent.parent / "session.json"


def load_session() -> list | None:
    if SESSION_PATH.exists():
        return json.loads(SESSION_PATH.read_text(encoding="utf-8"))
    return None


def save_session(cookies: list) -> None:
    SESSION_PATH.write_text(json.dumps(cookies, indent=2), encoding="utf-8")


def _is_logged_in(context: BrowserContext) -> bool:
    page = context.new_page()
    try:
        page.goto(os.environ["KLZ_BASE_URL"], timeout=15_000)
        return "login" not in page.url
    finally:
        page.close()


def _do_login(context: BrowserContext) -> None:
    """
    IMPORTANT: Verify the CSS selectors below against the live login form at
    KLZ_LOGIN_URL before the first production run. Adjust if the form uses
    different input names or button selectors.
    """
    page = context.new_page()
    try:
        page.goto(os.environ["KLZ_LOGIN_URL"], timeout=15_000)
        page.fill("input[type='email'], input[name='username']",
                  os.environ["KLZ_USERNAME"])
        page.fill("input[type='password']", os.environ["KLZ_PASSWORD"])
        page.click("button[type='submit'], input[type='submit']")
        page.wait_for_url(lambda url: "login" not in url, timeout=15_000)
    finally:
        page.close()


def get_authenticated_context(playwright: Playwright) -> BrowserContext:
    browser = playwright.chromium.launch(headless=True)
    context = browser.new_context()

    cookies = load_session()
    if cookies:
        context.add_cookies(cookies)
        if _is_logged_in(context):
            return context

    _do_login(context)
    save_session(context.cookies())
    return context
