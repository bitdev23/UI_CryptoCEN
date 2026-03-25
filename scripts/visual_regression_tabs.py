from __future__ import annotations

import argparse
import datetime as dt
import os
from pathlib import Path
import requests


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default="http://127.0.0.1:5000")
    parser.add_argument("--path", default="/")
    parser.add_argument("--out-dir", default="artifacts/visual-regression")
    parser.add_argument("--wait-ms", type=int, default=900)
    parser.add_argument("--full-page", action="store_true")
    parser.add_argument("--headless", action="store_true", default=True)
    parser.add_argument("--allow-fallback", action="store_true", help="Capture a single page screenshot even if dashboard tabs are unavailable")
    parser.add_argument("--login-email", default=os.getenv("VISREG_EMAIL", ""))
    parser.add_argument("--login-password", default=os.getenv("VISREG_PASSWORD", ""))
    return parser.parse_args()


def login_and_get_tokens(base_url: str, email: str, password: str) -> tuple[str, str]:
    payload = {"email": email, "password": password}
    response = requests.post(f"{base_url}/api/auth/login", json=payload, timeout=25)
    response.raise_for_status()
    data = response.json()
    if not data.get("success"):
        raise RuntimeError(data.get("message") or "login failed")
    access = str(data.get("access_token") or "").strip()
    refresh = str(data.get("refresh_token") or "").strip()
    if not access:
        raise RuntimeError("login succeeded but access_token was missing")
    return access, refresh


def seed_auth_tokens(page, base_url: str, access_token: str, refresh_token: str) -> None:
    page.goto(f"{base_url}/login", wait_until="domcontentloaded")
    page.evaluate(
        """
        (tokens) => {
            localStorage.setItem('access_token', tokens.access);
            if (tokens.refresh) localStorage.setItem('refresh_token', tokens.refresh);
        }
        """,
        {"access": access_token, "refresh": refresh_token},
    )


def set_theme(page, dark: bool) -> None:
    value = "true" if dark else "false"
    page.evaluate(
        """
        (isDark) => {
            localStorage.setItem('velank-dark-mode', isDark ? 'true' : 'false');
            document.body.classList.toggle('dark-mode', isDark);
        }
        """,
        dark,
    )


def activate_tab(page, tab_id: str) -> None:
    page.evaluate(
        """
        (id) => {
            if (typeof switchTab === 'function') {
                switchTab(id, null, true);
                return;
            }

            const target = document.getElementById(id);
            if (!target) return;

            document.querySelectorAll('.tab-content').forEach((tab) => {
                tab.classList.remove('active');
                tab.style.display = 'none';
            });

            target.classList.add('active');
            target.style.display = '';

            document.querySelectorAll('.nav-item').forEach((item) => {
                item.classList.remove('active');
            });
            const nav = document.querySelector(`.nav-item[data-tab="${id}"]`);
            if (nav) nav.classList.add('active');
        }
        """,
        tab_id,
    )


def safe_name(value: str) -> str:
    return value.replace("/", "-").replace(" ", "-")


def main() -> int:
    args = parse_args()
    try:
        from playwright.sync_api import sync_playwright
    except Exception:
        print("Playwright is required. Install with: pip install playwright && playwright install chromium")
        return 1

    tabs = [
        "dashboard",
        "content-creator",
        "scheduler",
        "knowledge-base",
        "settings",
        "post-history",
        "help",
        "style-clone",
        "repurpose",
        "best-time",
    ]

    timestamp = dt.datetime.now().strftime("%Y%m%d-%H%M%S")
    root = Path(args.out_dir) / timestamp
    root.mkdir(parents=True, exist_ok=True)

    base = args.base_url.rstrip("/")
    path = args.path if args.path.startswith("/") else f"/{args.path}"
    target_url = f"{base}{path}"

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=args.headless)
        context = browser.new_context(viewport={"width": 1512, "height": 982})
        page = context.new_page()

        if args.login_email and args.login_password:
            access, refresh = login_and_get_tokens(base, args.login_email, args.login_password)
            seed_auth_tokens(page, base, access, refresh)

        page.goto(target_url, wait_until="networkidle")

        has_switch_tab = page.evaluate("typeof switchTab === 'function'")
        if not has_switch_tab:
            print("warning: dashboard tab API not found; using manual tab activation fallback.")
            if not args.allow_fallback:
                print("tip: if this still captures the wrong page, open an authenticated dashboard route and rerun with --path.")
            if "/login" in page.url and not (args.login_email and args.login_password):
                print("tip: auth gate detected. Provide --login-email/--login-password or VISREG_EMAIL/VISREG_PASSWORD.")

        for is_dark in (False, True):
            theme = "dark" if is_dark else "light"
            theme_dir = root / theme
            theme_dir.mkdir(parents=True, exist_ok=True)

            set_theme(page, is_dark)
            page.wait_for_timeout(args.wait_ms)

            if has_switch_tab or args.allow_fallback or page.evaluate("document.querySelectorAll('.tab-content').length > 0"):
                for tab in tabs:
                    activate_tab(page, tab)
                    page.wait_for_timeout(args.wait_ms)
                    file_path = theme_dir / f"{safe_name(tab)}.png"
                    page.screenshot(path=str(file_path), full_page=args.full_page)
                    print(f"saved: {file_path}")
            else:
                file_path = theme_dir / "page.png"
                page.screenshot(path=str(file_path), full_page=args.full_page)
                print(f"saved: {file_path}")

        browser.close()

    print(f"visual regression snapshots written to: {root}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
