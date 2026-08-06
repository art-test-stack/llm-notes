#!/usr/bin/env python3
from __future__ import annotations

import argparse
import shutil
import tempfile
import threading
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from playwright.sync_api import expect, sync_playwright

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SITE = ROOT / "site"


class QuietHandler(SimpleHTTPRequestHandler):
    def log_message(self, format: str, *args: object) -> None:
        return


def find_browser() -> str:
    for name in ("google-chrome", "google-chrome-stable", "chromium", "chromium-browser"):
        path = shutil.which(name)
        if path:
            return path
    raise SystemExit("No supported Chromium browser found for the smoke test")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--site", type=Path, default=DEFAULT_SITE)
    args = parser.parse_args()
    site = args.site.resolve()
    browser_path = find_browser()

    with tempfile.TemporaryDirectory(prefix="llm-notes-browser-") as temp_name:
        root = Path(temp_name)
        shutil.copytree(site, root / "llm-notes")
        handler = lambda *a, **kw: QuietHandler(*a, directory=str(root), **kw)
        server = ThreadingHTTPServer(("127.0.0.1", 0), handler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        base = f"http://localhost:{server.server_port}/llm-notes"

        try:
            with sync_playwright() as playwright:
                browser = playwright.chromium.launch(
                    executable_path=browser_path,
                    headless=True,
                    args=[
                        "--disable-dev-shm-usage",
                        "--no-sandbox",
                        "--no-proxy-server",
                        "--proxy-bypass-list=*",
                    ],
                )
                context = browser.new_context(service_workers="allow")
                page = context.new_page()
                browser_errors: list[str] = []
                page.on("pageerror", lambda error: browser_errors.append(str(error)))
                page.on(
                    "requestfailed",
                    lambda request: browser_errors.append(
                        f"request failed: {request.url} ({request.failure})"
                    ),
                )

                page.goto(base + "/index.html", wait_until="load")
                expect(page.locator("[data-status]")).to_have_text("Ready.", timeout=10_000)

                page.goto(base + "/topics/index.html", wait_until="load")
                expect(page.locator("[data-count]")).to_have_text("40 results")

                page.goto(base + "/topics/pytorch-data-loading.html", wait_until="load")
                assert page.locator(".syntax-keyword").count() > 0

                page.goto(base + "/404.html", wait_until="load")
                expect(page.locator("#home")).to_have_attribute("href", "/llm-notes/index.html")

                assert not browser_errors, "\n".join(browser_errors)
                context.close()
                browser.close()
        finally:
            server.shutdown()
            thread.join(timeout=5)

    print(f"Browser smoke test passed with {Path(browser_path).name}.")


if __name__ == "__main__":
    main()
