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
    import os
    fd = os.open(SESSION_PATH, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        f.write(json.dumps(cookies, indent=2))


def _is_logged_in(context: BrowserContext) -> bool:
    page = context.new_page()
    try:
        page.goto(os.environ["KLZ_BASE_URL"], timeout=15_000)
        return "login" not in page.url
    finally:
        page.close()


def _do_login(context: BrowserContext) -> None:
    # kleinezeitung.at login uses a Piano/TinyPass iframe modal (id.tinypass.com)
    page = context.new_page()
    try:
        page.goto(os.environ["KLZ_LOGIN_URL"], timeout=15_000)
        login_btn = page.get_by_text("EINLOGGEN")
        if login_btn.is_visible():
            login_btn.click()
        page.wait_for_selector("iframe[src*='tinypass']", timeout=15_000)
        frame = page.frame_locator("iframe[src*='tinypass']")
        frame.locator("input#email").fill(os.environ["KLZ_USERNAME"])
        frame.locator("input#password").fill(os.environ["KLZ_PASSWORD"])
        frame.locator("button[type='submit']").click()
        page.wait_for_load_state("networkidle", timeout=15_000)
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
