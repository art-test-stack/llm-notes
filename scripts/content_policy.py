#!/usr/bin/env python3
"""Public-content schema, chapter-integrity, and privacy checks."""
from __future__ import annotations

import base64
import hashlib
import html
import json
import os
import re
from collections.abc import Iterable
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlsplit

TOPIC_KEYS = {"id", "title", "track", "summary", "prerequisites", "connections"}
EXPORT_TOPIC_KEYS = {"id", "title", "track", "prerequisites", "connections", "chapter"}
GLOSSARY_KEYS = {"id", "term", "definition"}
MANIFEST_KEYS = {"schema_version", "chapter_count", "total_characters", "chapters"}
MANIFEST_ENTRY_KEYS = {"id", "file", "sha256", "characters", "sections"}
ID_PATTERN = re.compile(r"[a-z0-9]+(?:-[a-z0-9]+)*")
TAG_RE = re.compile(r"<[^>]+>")

GENERIC_LEAK_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("email address", re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.IGNORECASE)),
    ("local user path", re.compile(r"(?:/Users/[^/\s]+/|/home/[^/\s]+/|[A-Za-z]:\\Users\\[^\\\s]+\\)")),
    ("credential-like token", re.compile(r"\b(?:github_pat_[A-Za-z0-9_]{12,}|ghp_[A-Za-z0-9]{20,}|sk-[A-Za-z0-9_-]{20,}|xox[baprs]-[A-Za-z0-9-]{20,}|AKIA[0-9A-Z]{16})\b")),
    ("internal-network URL", re.compile(r"https?://(?:localhost|127(?:\.\d{1,3}){3}|10(?:\.\d{1,3}){3}|192\.168(?:\.\d{1,3}){2}|172\.(?:1[6-9]|2\d|3[01])(?:\.\d{1,3}){2})(?::\d+)?", re.IGNORECASE)),
    ("active embedded content", re.compile(r"(?:<\s*(?:script|iframe|object|embed)\b|javascript\s*:)", re.IGNORECASE)),
)


class FragmentParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.ids: list[str] = []
        self.links: list[str] = []
        self.h2_count = 0
        self.section_topics: list[str] = []
        self.forbidden_tags: list[str] = []

    def handle_starttag(self, tag: str, attrs) -> None:
        values = dict(attrs)
        if values.get("id"):
            self.ids.append(values["id"])
        if tag == "h2":
            self.h2_count += 1
        if tag == "section" and values.get("data-topic"):
            self.section_topics.append(values["data-topic"])
        if tag in {"script", "style", "iframe", "object", "embed", "form", "link"}:
            self.forbidden_tags.append(tag)
        if tag == "a" and values.get("href"):
            self.links.append(values["href"])
        if tag in {"img", "audio", "video", "source"} and values.get("src"):
            self.links.append(values["src"])


def plain_text(value: str) -> str:
    return " ".join(html.unescape(TAG_RE.sub(" ", value)).split())


def iter_public_strings(topics: list[dict], glossary: list[dict]) -> Iterable[tuple[str, str]]:
    for index, topic in enumerate(topics):
        for key in ("id", "title", "track", "summary"):
            yield f"topics.json[{index}].{key}", topic[key]
        for key in ("prerequisites", "connections"):
            for item_index, value in enumerate(topic[key]):
                yield f"topics.json[{index}].{key}[{item_index}]", value
    for index, entry in enumerate(glossary):
        for key in ("id", "term", "definition"):
            yield f"glossary.json[{index}].{key}", entry[key]


def _optional_private_patterns() -> list[re.Pattern[str]]:
    encoded = os.environ.get("PUBLICATION_DENYLIST_B64", "").strip()
    if not encoded:
        return []
    try:
        payload = json.loads(base64.b64decode(encoded, validate=True).decode("utf-8"))
    except Exception as exc:
        raise ValueError("PUBLICATION_DENYLIST_B64 is not valid base64-encoded JSON") from exc
    if not isinstance(payload, list) or not payload or not all(isinstance(item, str) and item for item in payload):
        raise ValueError("PUBLICATION_DENYLIST_B64 must encode a non-empty JSON list of regex strings")
    try:
        return [re.compile(item, re.IGNORECASE) for item in payload]
    except re.error as exc:
        raise ValueError("PUBLICATION_DENYLIST_B64 contains an invalid regular expression") from exc


def validate_public_text(text: str, location: str, *, private_patterns: list[re.Pattern[str]] | None = None) -> None:
    for label, pattern in GENERIC_LEAK_PATTERNS:
        if pattern.search(text):
            raise ValueError(f"Potential {label} in {location}")
    for index, pattern in enumerate(private_patterns or []):
        if pattern.search(text):
            raise ValueError(f"Restricted publication pattern #{index + 1} matched in {location}")


def validate_public_content(topics: object, glossary: object) -> tuple[list[dict], list[dict]]:
    if not isinstance(topics, list) or not isinstance(glossary, list):
        raise ValueError("topics.json and glossary.json must both contain JSON lists")
    if not topics or not glossary:
        raise ValueError("Public content lists must not be empty")

    topic_ids: list[str] = []
    for index, topic in enumerate(topics):
        if not isinstance(topic, dict) or set(topic) != TOPIC_KEYS:
            raise ValueError(f"Invalid topic schema at index {index}")
        if not all(isinstance(topic[key], str) and topic[key].strip() for key in ("id", "title", "track", "summary")):
            raise ValueError(f"Invalid topic string field at index {index}")
        if ID_PATTERN.fullmatch(topic["id"]) is None:
            raise ValueError(f"Invalid topic ID at index {index}")
        for key in ("prerequisites", "connections"):
            if not isinstance(topic[key], list) or not all(isinstance(value, str) for value in topic[key]):
                raise ValueError(f"Invalid {key} list at topic index {index}")
        topic_ids.append(topic["id"])

    if len(topic_ids) != len(set(topic_ids)):
        raise ValueError("Duplicate topic IDs")
    known = set(topic_ids)
    for index, topic in enumerate(topics):
        related = topic["prerequisites"] + topic["connections"]
        if any(value not in known for value in related):
            raise ValueError(f"Unknown topic relationship at index {index}")
        if topic["id"] in related:
            raise ValueError(f"Self-referential topic relationship at index {index}")

    glossary_ids: list[str] = []
    glossary_terms: list[str] = []
    for index, entry in enumerate(glossary):
        if not isinstance(entry, dict) or set(entry) != GLOSSARY_KEYS:
            raise ValueError(f"Invalid glossary schema at index {index}")
        if not all(isinstance(entry[key], str) and entry[key].strip() for key in GLOSSARY_KEYS):
            raise ValueError(f"Invalid glossary string field at index {index}")
        if ID_PATTERN.fullmatch(entry["id"]) is None:
            raise ValueError(f"Invalid glossary ID at index {index}")
        glossary_ids.append(entry["id"])
        glossary_terms.append(entry["term"].casefold())
    if len(glossary_ids) != len(set(glossary_ids)):
        raise ValueError("Duplicate glossary IDs")
    if len(glossary_terms) != len(set(glossary_terms)):
        raise ValueError("Duplicate glossary terms")

    private_patterns = _optional_private_patterns()
    for location, value in iter_public_strings(topics, glossary):
        validate_public_text(value, location, private_patterns=private_patterns)
    return topics, glossary


def validate_export_topics(exported: object, public_topics: list[dict]) -> list[dict]:
    if not isinstance(exported, list) or len(exported) != len(public_topics):
        raise ValueError("Exported topics must cover the complete public topic registry")
    public_by_id = {topic["id"]: topic for topic in public_topics}
    seen: set[str] = set()
    for index, item in enumerate(exported):
        if not isinstance(item, dict) or set(item) != EXPORT_TOPIC_KEYS:
            raise ValueError(f"Invalid exported topic schema at index {index}")
        topic_id = item["id"]
        if topic_id in seen or topic_id not in public_by_id:
            raise ValueError(f"Unknown or duplicate exported topic at index {index}")
        seen.add(topic_id)
        public = public_by_id[topic_id]
        for key in ("title", "track", "prerequisites", "connections"):
            if item[key] != public[key]:
                raise ValueError(f"Export metadata mismatch for {topic_id}.{key}")
        if item["chapter"] != f"chapters/{topic_id}.html":
            raise ValueError(f"Unexpected chapter path for {topic_id}")
    return exported


def validate_chapter_bundle(content_root: Path, topics: list[dict]) -> dict:
    chapters_dir = content_root / "chapters"
    manifest_path = content_root / "chapter-manifest.json"
    if not chapters_dir.is_dir() or not manifest_path.is_file():
        raise ValueError("Missing chapters directory or chapter-manifest.json")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if not isinstance(manifest, dict) or set(manifest) != MANIFEST_KEYS or manifest["schema_version"] != 1:
        raise ValueError("Invalid chapter manifest schema")
    entries = manifest["chapters"]
    if not isinstance(entries, list) or manifest["chapter_count"] != len(topics) or len(entries) != len(topics):
        raise ValueError("Chapter manifest does not cover every topic")
    topic_ids = {topic["id"] for topic in topics}
    actual_files = {path.name for path in chapters_dir.glob("*.html")}
    expected_files = {f"{topic_id}.html" for topic_id in topic_ids}
    if actual_files != expected_files:
        raise ValueError("Chapter directory does not exactly match the topic registry")
    entry_ids: set[str] = set()
    total_characters = 0
    private_patterns = _optional_private_patterns()
    for index, entry in enumerate(entries):
        if not isinstance(entry, dict) or set(entry) != MANIFEST_ENTRY_KEYS:
            raise ValueError(f"Invalid chapter manifest entry at index {index}")
        topic_id = entry["id"]
        if topic_id not in topic_ids or topic_id in entry_ids:
            raise ValueError(f"Unknown or duplicate chapter manifest ID at index {index}")
        entry_ids.add(topic_id)
        expected_file = f"chapters/{topic_id}.html"
        if entry["file"] != expected_file:
            raise ValueError(f"Unexpected chapter manifest path for {topic_id}")
        path = content_root / expected_file
        raw = path.read_text(encoding="utf-8")
        if hashlib.sha256(raw.encode("utf-8")).hexdigest() != entry["sha256"]:
            raise ValueError(f"Chapter hash mismatch for {topic_id}")
        validate_public_text(raw, expected_file, private_patterns=private_patterns)
        parser = FragmentParser()
        parser.feed(raw)
        if parser.forbidden_tags:
            raise ValueError(f"Forbidden tags in {expected_file}: {sorted(set(parser.forbidden_tags))}")
        if parser.section_topics != [topic_id]:
            raise ValueError(f"Chapter root does not identify {topic_id}")
        if len(parser.ids) != len(set(parser.ids)):
            raise ValueError(f"Duplicate fragment IDs in {expected_file}")
        if parser.h2_count < 3 or parser.h2_count != entry["sections"]:
            raise ValueError(f"Section count mismatch for {topic_id}")
        characters = len(plain_text(raw))
        if characters < 1500 or characters != entry["characters"]:
            raise ValueError(f"Character count mismatch for {topic_id}")
        for href in parser.links:
            url = urlsplit(href)
            if url.scheme or href.startswith("//") or href.startswith(("mailto:", "tel:")):
                raise ValueError(f"External link in {expected_file}: {href}")
            if url.path and Path(url.path).name not in expected_files:
                raise ValueError(f"Unknown chapter link in {expected_file}: {href}")
        if "source-basis" in raw.casefold() or ">source basis<" in raw.casefold():
            raise ValueError(f"Private provenance section in {expected_file}")
        total_characters += characters
    if entry_ids != topic_ids or manifest["total_characters"] != total_characters:
        raise ValueError("Chapter manifest totals do not match chapter content")
    return manifest


def scan_repository_with_optional_policy(root: Path) -> None:
    private_patterns = _optional_private_patterns()
    if not private_patterns:
        return
    for path in sorted(root.rglob("*")):
        if not path.is_file() or ".git" in path.parts or "__pycache__" in path.parts or path.suffix.lower() in {".pyc", ".png", ".ico"}:
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        for index, pattern in enumerate(private_patterns):
            if pattern.search(text):
                raise ValueError(f"Restricted publication pattern #{index + 1} matched in {path.relative_to(root)}")
