#!/usr/bin/env python3
from __future__ import annotations

import argparse
import re
import subprocess
import tempfile
from pathlib import Path

from harden_site import DEFAULT_SITE, VERSION_RE, content_digest

INLINE_SCRIPT_RE = re.compile(r"<script>(?P<script>.*?)</script>", re.DOTALL | re.IGNORECASE)


def check_javascript(source: str, label: str) -> None:
    with tempfile.NamedTemporaryFile("w", suffix=".js", encoding="utf-8") as handle:
        handle.write(source)
        handle.flush()
        subprocess.run(["node", "--check", handle.name], check=True)
    print(f"Validated JavaScript syntax: {label}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--site", type=Path, default=DEFAULT_SITE)
    args = parser.parse_args()
    site = args.site.resolve()

    worker_path = site / "service-worker.js"
    worker = worker_path.read_text(encoding="utf-8")
    match = VERSION_RE.search(worker)
    assert match is not None, "Missing service-worker cache version"
    actual = match.group(0).split('"', 2)[1]
    expected = content_digest(site)
    assert actual == expected, f"Stale service-worker version: {actual} != {expected}"
    assert "self.skipWaiting()" in worker
    assert "self.clients.claim()" in worker

    not_found = (site / "404.html").read_text(encoding="utf-8")
    assert "assets/" not in not_found, "404 page must not rely on path-relative assets"
    assert 'id="home"' in not_found
    assert "location.pathname.startsWith(marker)" in not_found
    inline_scripts = INLINE_SCRIPT_RE.findall(not_found)
    assert len(inline_scripts) == 1, "Expected one inline script in the self-contained 404 page"
    check_javascript(inline_scripts[0], "404.html")

    for script in sorted((site / "assets").glob("*.js")) + [worker_path]:
        subprocess.run(["node", "--check", str(script)], check=True)

    print(f"Validated hardened runtime assets and cache version {actual}.")


if __name__ == "__main__":
    main()
