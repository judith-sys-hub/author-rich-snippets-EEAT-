"""Opens a real Chrome window for one-time Instagram + X login.

Uses a persistent browser profile in socialcheck/.browser_profile (gitignored),
launched as real Chrome with automation markers disabled so the platforms
don't flag the login as a bot. Credentials are never seen by this script.

The check script (check_private.py) reuses the same profile afterwards.
"""

import time
from pathlib import Path

from playwright.sync_api import Error as PlaywrightError, sync_playwright

PROFILE_DIR = Path(__file__).parent / ".browser_profile"

IG_COOKIE = "sessionid"  # set on .instagram.com after login
X_COOKIE = "auth_token"  # set on .x.com after login

LAUNCH_KWARGS = dict(
    channel="chrome",
    headless=False,
    locale="de-AT",
    args=["--disable-blink-features=AutomationControlled"],
    ignore_default_args=["--enable-automation"],
)


def _has_cookie(context, domain_part: str, name: str) -> bool:
    return any(
        c["name"] == name and domain_part in c["domain"] and c["value"]
        for c in context.cookies()
    )


def main() -> None:
    with sync_playwright() as p:
        context = p.chromium.launch_persistent_context(str(PROFILE_DIR), **LAUNCH_KWARGS)

        ig_page = context.new_page()
        ig_page.goto("https://www.instagram.com/accounts/login/")
        x_page = context.new_page()
        x_page.goto("https://x.com/i/flow/login")

        print("Bitte in BEIDEN Tabs einloggen (Instagram + X).")
        print("Das Skript erkennt den Login automatisch.")
        print("Fenster bitte NICHT schliessen - es schliesst sich von selbst.")

        ig_done = x_done = False
        for _ in range(900):  # max ~15 minutes
            try:
                if not ig_done and _has_cookie(context, "instagram.com", IG_COOKIE):
                    ig_done = True
                    print("[OK] Instagram-Login erkannt.")
                if not x_done and _has_cookie(context, "x.com", X_COOKIE):
                    x_done = True
                    print("[OK] X-Login erkannt.")
            except PlaywrightError:
                print("[INFO] Browser wurde geschlossen.")
                break
            if ig_done and x_done:
                break
            time.sleep(1)

        if ig_done and x_done:
            print("Beide Logins erkannt - Profil gespeichert, fertig.")
        else:
            missing = [n for n, ok in [("Instagram", ig_done), ("X", x_done)] if not ok]
            print(f"[WARN] Kein Login erkannt fuer: {', '.join(missing)}.")

        try:
            context.close()
        except PlaywrightError:
            pass


if __name__ == "__main__":
    main()
