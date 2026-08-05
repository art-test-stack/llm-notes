#!/usr/bin/env python3
from __future__ import annotations

import json
import subprocess
import sys
from collections import Counter
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urlsplit

from content_policy import scan_repository_with_optional_policy, validate_chapter_bundle, validate_public_content

ROOT = Path(__file__).resolve().parents[1]
SITE = ROOT / "site"
FORBIDDEN_RUNTIME = (
    "google-analytics",
    "googletagmanager",
    "segment.io",
    "mixpanel",
    "hotjar",
    "clarity.ms",
    "cdn.jsdelivr.net",
    "unpkg.com",
)
FORBIDDEN_BACKGROUND = (
    "periodicsync",
    "sync.register",
    "pushmanager",
    "shownotification(",
    "setinterval(",
    "websocket",
)


class Page(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.links: list[str] = []
        self.ids: list[str] = []
        self.h1 = 0
        self.h2 = 0
        self.chapter_topics: list[str] = []
        self.native_mathml = 0
        self.rendered_math_wrappers = 0
        self.unrendered_tex = 0

    def handle_starttag(self, tag: str, attrs) -> None:
        values = dict(attrs)
        if tag == "h1":
            self.h1 += 1
        if tag == "h2":
            self.h2 += 1
        if values.get("id"):
            self.ids.append(values["id"])
        if tag == "section" and values.get("data-topic"):
            self.chapter_topics.append(values["data-topic"])
        if tag == "math":
            self.native_mathml += 1
        if values.get("data-rendered") == "katex-mathml":
            self.rendered_math_wrappers += 1
        if values.get("data-tex"):
            self.unrendered_tex += 1
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
    topics_raw = json.loads((ROOT / "content/topics.json").read_text(encoding="utf-8"))
    glossary_raw = json.loads((ROOT / "content/glossary.json").read_text(encoding="utf-8"))
    topics, glossary = validate_public_content(topics_raw, glossary_raw)
    chapter_manifest = validate_chapter_bundle(ROOT / "content", topics)
    scan_repository_with_optional_policy(ROOT)
    subprocess.run([sys.executable, str(ROOT / "scripts/build_site.py")], check=True)

    assert len(topics) == 39 and len(glossary) >= 50
    assert chapter_manifest["chapter_count"] == len(topics)
    assert chapter_manifest["total_characters"] >= 500_000
    assert chapter_manifest["total_math_expressions"] >= 1_000

    manifest = json.loads((SITE / "manifest.webmanifest").read_text(encoding="utf-8"))
    assert manifest["start_url"].startswith("./")
    assert manifest["scope"] == "./"
    assert manifest["display"] == "standalone"

    sw = (SITE / "service-worker.js").read_text(encoding="utf-8").casefold()
    assert "cache_library" in sw and "refresh_library" in sw
    assert 'const v="v3"' in sw
    for marker in FORBIDDEN_BACKGROUND:
        assert marker not in sw, f"Forbidden background behavior: {marker}"

    site_text = "\n".join(
        path.read_text(encoding="utf-8")
        for path in SITE.rglob("*")
        if path.is_file() and path.suffix.lower() not in {".png", ".ico"}
    ).casefold()
    for marker in FORBIDDEN_RUNTIME:
        assert marker not in site_text, f"Forbidden runtime dependency: {marker}"
    assert "data-tex=" not in site_text, "Unrendered TeX source escaped into the deployed site"
    assert "katex.min.js" not in site_text and "auto-render" not in site_text

    parsed: dict[Path, Page] = {}
    topic_ids = {topic["id"] for topic in topics}
    total_mathml = 0
    total_wrappers = 0
    for path in sorted(SITE.rglob("*.html")):
        page = parse(path)
        parsed[path.resolve()] = page
        assert page.h1 == 1, f"Expected one h1 in {path.relative_to(ROOT)}"
        assert not [item for item, count in Counter(page.ids).items() if count > 1]
        assert page.unrendered_tex == 0
        total_mathml += page.native_mathml
        total_wrappers += page.rendered_math_wrappers
        if path.parent.name == "topics" and path.name != "index.html":
            topic_id = path.stem
            assert topic_id in topic_ids
            assert page.chapter_topics == [topic_id], f"Missing substantive chapter in {path.relative_to(ROOT)}"
            assert page.h2 >= 3
            expected_math = next(
                item["math_expressions"] for item in chapter_manifest["chapters"] if item["id"] == topic_id
            )
            assert page.native_mathml == expected_math, f"MathML count mismatch in {path.relative_to(ROOT)}"
            assert page.rendered_math_wrappers == expected_math
            assert path.stat().st_size >= 4_000

    expected_total = chapter_manifest["total_math_expressions"]
    assert total_mathml == expected_total, f"Rendered {total_mathml} MathML expressions, expected {expected_total}"
    assert total_wrappers == expected_total

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
        f"Validated {len(topics)} substantive chapters "
        f"({chapter_manifest['total_characters']:,} text characters), "
        f"{expected_total:,} static MathML expressions, {len(glossary)} definitions, "
        f"{len(parsed)} HTML pages, privacy policy, links, and PWA constraints."
    )


if __name__ == "__main__":
    main()
