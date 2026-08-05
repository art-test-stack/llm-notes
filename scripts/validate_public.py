#!/usr/bin/env python3
from __future__ import annotations

import json
import subprocess
import sys
from collections import Counter
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urlsplit

from content_policy import scan_repository_with_optional_policy, validate_public_content

ROOT = Path(__file__).resolve().parents[1]
SITE = ROOT / "site"
FORBIDDEN_RUNTIME = ("google-analytics", "googletagmanager", "segment.io", "mixpanel", "hotjar", "clarity.ms")
FORBIDDEN_BACKGROUND = ("periodicsync", "sync.register", "pushmanager", "shownotification(", "setinterval(", "websocket")


class Page(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.links: list[str] = []
        self.ids: list[str] = []
        self.h1 = 0

    def handle_starttag(self, tag: str, attrs) -> None:
        values = dict(attrs)
        if tag == "h1":
            self.h1 += 1
        if values.get("id"):
            self.ids.append(values["id"])
        if tag in {"a", "link"} and values.get("href"):
            self.links.append(values["href"])
        if tag in {"script", "img"} and values.get("src"):
            self.links.append(values["src"])


def parse(path: Path) -> Page:
    page = Page()
    page.feed(path.read_text(encoding="utf-8"))
    return page


def resolve(source: Path, href: str) -> tuple[Path, str] | None:
    url = urlsplit(href)
    if url.scheme or href.startswith("//") or href.startswith(("mailto:", "tel:")):
        return None
    target = source if not url.path else source.parent / unquote(url.path)
    target = target.resolve()
    if url.path.endswith("/") or target.is_dir():
        target /= "index.html"
    return target, unquote(url.fragment)


def main() -> None:
    subprocess.run([sys.executable, str(ROOT / "scripts/build_site.py")], check=True)

    topics_raw = json.loads((ROOT / "content/topics.json").read_text(encoding="utf-8"))
    glossary_raw = json.loads((ROOT / "content/glossary.json").read_text(encoding="utf-8"))
    topics, glossary = validate_public_content(topics_raw, glossary_raw)
    scan_repository_with_optional_policy(ROOT)

    assert len(topics) == 39
    assert len(glossary) >= 50
    for topic in topics:
        assert (SITE / "topics" / f'{topic["id"]}.html').is_file()

    manifest = json.loads((SITE / "manifest.webmanifest").read_text(encoding="utf-8"))
    assert manifest["start_url"].startswith("./")
    assert manifest["scope"] == "./"
    assert manifest["display"] == "standalone"

    sw = (SITE / "service-worker.js").read_text(encoding="utf-8").casefold()
    assert "cache_library" in sw and "refresh_library" in sw
    for marker in FORBIDDEN_BACKGROUND:
        assert marker not in sw, f"Forbidden background behavior: {marker}"

    site_text = "\n".join(
        path.read_text(encoding="utf-8")
        for path in SITE.rglob("*")
        if path.is_file() and path.suffix.lower() not in {".png", ".ico"}
    ).casefold()
    for marker in FORBIDDEN_RUNTIME:
        assert marker not in site_text, f"Forbidden runtime dependency: {marker}"

    parsed: dict[Path, Page] = {}
    for path in sorted(SITE.rglob("*.html")):
        page = parse(path)
        parsed[path.resolve()] = page
        assert page.h1 == 1, f"Expected one h1 in {path.relative_to(ROOT)}"
        assert not [item for item, count in Counter(page.ids).items() if count > 1]

    for source, page in parsed.items():
        for href in page.links:
            resolved = resolve(source, href)
            assert resolved is not None, f"External link or asset in {source.relative_to(ROOT)}: {href}"
            target, fragment = resolved
            assert target.is_file(), f"Broken link in {source.relative_to(ROOT)}: {href}"
            if fragment and target.suffix == ".html":
                assert fragment in (parsed.get(target) or parse(target)).ids

    library = json.loads((SITE / "precache-library.json").read_text(encoding="utf-8"))
    assert {f'topics/{topic["id"]}.html' for topic in topics} <= set(library)
    print(
        f"Validated {len(topics)} topics, {len(glossary)} definitions, "
        f"{len(parsed)} HTML pages, structural privacy policy, links, and PWA constraints."
    )


if __name__ == "__main__":
    main()
