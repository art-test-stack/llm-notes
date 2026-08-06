#!/usr/bin/env python3
from __future__ import annotations

import json
import re
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
CSS_URL = re.compile(r"url\((?P<quote>['\"]?)(?P<url>[^)'\"]+)(?P=quote)\)")


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
        self.katex_roots = 0
        self.katex_visual_layers = 0
        self.katex_accessible_layers = 0
        self.unrendered_tex = 0

    def handle_starttag(self, tag: str, attrs) -> None:
        values = dict(attrs)
        classes = set((values.get("class") or "").split())
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
        if values.get("data-rendered") == "katex-static":
            self.rendered_math_wrappers += 1
        if "katex" in classes:
            self.katex_roots += 1
        if "katex-html" in classes:
            self.katex_visual_layers += 1
        if "katex-mathml" in classes:
            self.katex_accessible_layers += 1
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


def validate_promotions(path: Path, topic_ids: set[str]) -> tuple[dict[str, int], int]:
    raw = json.loads(path.read_text(encoding="utf-8"))
    assert isinstance(raw, dict) and raw.get("schema_version") == 1
    assert isinstance(raw.get("chapters"), dict)
    declared_total = raw.get("total_occurrences")
    assert isinstance(declared_total, int) and declared_total >= 1
    by_topic: dict[str, int] = {}
    seen_pairs: set[tuple[str, str]] = set()
    calculated_total = 0
    for topic_id, entries in raw["chapters"].items():
        assert topic_id in topic_ids
        assert isinstance(entries, list) and entries
        topic_total = 0
        for entry in entries:
            assert isinstance(entry, dict) and set(entry) == {"text", "tex", "occurrences"}
            assert isinstance(entry["text"], str) and entry["text"].strip()
            assert isinstance(entry["tex"], str) and entry["tex"].strip()
            assert isinstance(entry["occurrences"], int) and entry["occurrences"] >= 1
            pair = (topic_id, entry["text"])
            assert pair not in seen_pairs
            seen_pairs.add(pair)
            topic_total += entry["occurrences"]
        by_topic[topic_id] = topic_total
        calculated_total += topic_total
    assert calculated_total == declared_total
    return by_topic, declared_total


def validate_katex_assets(library: set[str]) -> int:
    root = SITE / "assets" / "katex"
    css_path = root / "katex.min.css"
    font_root = root / "fonts"
    assert css_path.is_file(), "Missing local KaTeX stylesheet"
    assert font_root.is_dir(), "Missing local KaTeX fonts"
    css = css_path.read_text(encoding="utf-8")
    assert ".katex-html" in css and ".katex-mathml" in css
    assert "position:absolute" in css.replace(" ", ""), "KaTeX accessibility layer is not visually hidden"
    referenced: set[str] = set()
    for match in CSS_URL.finditer(css):
        value = match.group("url").strip()
        parsed = urlsplit(value)
        assert not parsed.scheme and not value.startswith("//"), f"External KaTeX asset: {value}"
        target = (css_path.parent / unquote(parsed.path)).resolve()
        assert target.is_file(), f"Missing KaTeX asset referenced by CSS: {value}"
        referenced.add(target.relative_to(SITE).as_posix())
    assert len(referenced) >= 10, "Unexpectedly small KaTeX font set"
    all_assets = {
        path.relative_to(SITE).as_posix()
        for path in root.rglob("*")
        if path.is_file()
    }
    assert "assets/katex/katex.min.css" in all_assets
    assert all_assets <= library, "KaTeX assets are not all included in the manual offline library"
    return len(referenced)


def main() -> None:
    topics_raw = json.loads((ROOT / "content/topics.json").read_text(encoding="utf-8"))
    glossary_raw = json.loads((ROOT / "content/glossary.json").read_text(encoding="utf-8"))
    topics, glossary = validate_public_content(topics_raw, glossary_raw)
    chapter_manifest = validate_chapter_bundle(ROOT / "content", topics)
    topic_ids = {topic["id"] for topic in topics}
    promoted_by_topic, promoted_total = validate_promotions(ROOT / "content/math-code-promotions.json", topic_ids)
    scan_repository_with_optional_policy(ROOT)
    subprocess.run([sys.executable, str(ROOT / "scripts/build_site.py")], check=True)

    assert len(topics) == 40 and len(glossary) >= 50
    assert chapter_manifest["chapter_count"] == len(topics)
    assert chapter_manifest["total_characters"] >= 500_000
    assert chapter_manifest["total_math_expressions"] >= 1_000

    manifest = json.loads((SITE / "manifest.webmanifest").read_text(encoding="utf-8"))
    assert manifest["start_url"].startswith("./")
    assert manifest["scope"] == "./"
    assert manifest["display"] == "standalone"

    sw = (SITE / "service-worker.js").read_text(encoding="utf-8").casefold()
    assert "cache_library" in sw and "refresh_library" in sw
    assert 'const v="v5"' in sw
    assert "assets/katex/katex.min.css" in sw
    for marker in FORBIDDEN_BACKGROUND:
        assert marker not in sw, f"Forbidden background behavior: {marker}"

    site_text = "\n".join(
        path.read_text(encoding="utf-8")
        for path in SITE.rglob("*")
        if path.is_file() and path.suffix.lower() not in {".png", ".ico", ".woff", ".woff2", ".ttf"}
    ).casefold()
    for marker in FORBIDDEN_RUNTIME:
        assert marker not in site_text, f"Forbidden runtime dependency: {marker}"
    assert "data-tex=" not in site_text, "Unrendered TeX source escaped into the deployed site"
    assert "katex.min.js" not in site_text and "auto-render" not in site_text

    parsed: dict[Path, Page] = {}
    totals = Counter()
    manifest_by_id = {item["id"]: item for item in chapter_manifest["chapters"]}
    for path in sorted(SITE.rglob("*.html")):
        page = parse(path)
        parsed[path.resolve()] = page
        assert page.h1 == 1, f"Expected one h1 in {path.relative_to(ROOT)}"
        assert not [item for item, count in Counter(page.ids).items() if count > 1]
        assert page.unrendered_tex == 0
        totals.update(
            mathml=page.native_mathml,
            wrappers=page.rendered_math_wrappers,
            roots=page.katex_roots,
            visual=page.katex_visual_layers,
            accessible=page.katex_accessible_layers,
        )
        if path.parent.name == "topics" and path.name != "index.html":
            topic_id = path.stem
            assert topic_id in topic_ids
            assert page.chapter_topics == [topic_id], f"Missing substantive chapter in {path.relative_to(ROOT)}"
            assert page.h2 >= 3
            expected_math = manifest_by_id[topic_id]["math_expressions"] + promoted_by_topic.get(topic_id, 0)
            for label, count in (
                ("MathML", page.native_mathml),
                ("static wrappers", page.rendered_math_wrappers),
                ("KaTeX roots", page.katex_roots),
                ("visual layers", page.katex_visual_layers),
                ("accessible layers", page.katex_accessible_layers),
            ):
                assert count == expected_math, f"{label} count mismatch in {path.relative_to(ROOT)}: {count} != {expected_math}"
            assert path.stat().st_size >= 4_000

    expected_total = chapter_manifest["total_math_expressions"] + promoted_total
    for label in ("mathml", "wrappers", "roots", "visual", "accessible"):
        assert totals[label] == expected_total, f"Rendered {totals[label]} {label} layers, expected {expected_total}"

    for source, page in parsed.items():
        for href in page.links:
            resolved = resolve(source, href)
            assert resolved is not None, f"External link or asset in {source.relative_to(ROOT)}: {href}"
            target, fragment = resolved
            assert target.is_file(), f"Broken link in {source.relative_to(ROOT)}: {href}"
            if fragment and target.suffix == ".html":
                assert fragment in (parsed.get(target) or parse(target)).ids

    library = set(json.loads((SITE / "precache-library.json").read_text(encoding="utf-8")))
    assert {f'topics/{topic["id"]}.html' for topic in topics} <= library
    font_count = validate_katex_assets(library)
    print(
        f"Validated {len(topics)} substantive chapters "
        f"({chapter_manifest['total_characters']:,} text characters), "
        f"{expected_total:,} static KaTeX expressions "
        f"({chapter_manifest['total_math_expressions']:,} canonical + {promoted_total:,} reviewed promotions), "
        f"{font_count} local math fonts, {len(glossary)} definitions, {len(parsed)} HTML pages, "
        "privacy policy, links, and PWA constraints."
    )


if __name__ == "__main__":
    main()
