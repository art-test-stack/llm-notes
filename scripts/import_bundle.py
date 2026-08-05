#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import shutil
import tempfile
import zipfile
from pathlib import Path

from content_policy import validate_chapter_bundle, validate_export_topics, validate_public_content

ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("bundle", type=Path)
    args = parser.parse_args()
    bundle = args.bundle.resolve()

    try:
        public_topics_raw = json.loads((ROOT / "content/topics.json").read_text(encoding="utf-8"))
        glossary_raw = json.loads((ROOT / "content/glossary.json").read_text(encoding="utf-8"))
        topics, _ = validate_public_content(public_topics_raw, glossary_raw)

        with tempfile.TemporaryDirectory() as temp_name:
            source = Path(temp_name) / "export"
            if bundle.is_dir():
                shutil.copytree(bundle, source)
            elif bundle.is_file() and bundle.suffix.lower() == ".zip":
                source.mkdir()
                with zipfile.ZipFile(bundle) as archive:
                    archive.extractall(source)
            else:
                raise ValueError("Bundle must be an extracted export directory or ZIP archive")

            entries = list(source.iterdir())
            files = {path.name for path in entries if path.is_file()}
            directories = {path.name for path in entries if path.is_dir()}
            if files != {"topics.json", "manifest.json"} or directories != {"chapters"}:
                raise ValueError("Bundle must contain exactly topics.json, manifest.json, and chapters/")

            exported = json.loads((source / "topics.json").read_text(encoding="utf-8"))
            validate_export_topics(exported, topics)

            validation_view = Path(temp_name) / "content"
            validation_view.mkdir()
            shutil.copyfile(source / "manifest.json", validation_view / "chapter-manifest.json")
            shutil.copytree(source / "chapters", validation_view / "chapters")
            validate_chapter_bundle(validation_view, topics)

            target = ROOT / "content"
            chapters = target / "chapters"
            if chapters.exists():
                shutil.rmtree(chapters)
            shutil.copytree(source / "chapters", chapters)
            shutil.copyfile(source / "manifest.json", target / "chapter-manifest.json")
    except (OSError, UnicodeError, json.JSONDecodeError, zipfile.BadZipFile, ValueError) as exc:
        raise SystemExit(f"Bundle rejected: {exc}") from exc

    print("Substantive chapter bundle imported. Run python3 scripts/validate_public.py before committing.")


if __name__ == "__main__":
    main()
