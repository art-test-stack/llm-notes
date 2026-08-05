#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path

from content_policy import validate_public_content

ROOT = Path(__file__).resolve().parents[1]
EXPECTED = {"topics.json", "glossary.json"}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("bundle", type=Path)
    args = parser.parse_args()
    bundle = args.bundle.resolve()
    if not bundle.is_dir():
        raise SystemExit(f"Not a directory: {bundle}")

    entries = list(bundle.iterdir())
    file_names = {path.name for path in entries if path.is_file()}
    if file_names != EXPECTED or any(path.is_dir() for path in entries):
        raise SystemExit(f"Bundle must contain exactly {sorted(EXPECTED)} and no directories")

    try:
        topics = json.loads((bundle / "topics.json").read_text(encoding="utf-8"))
        glossary = json.loads((bundle / "glossary.json").read_text(encoding="utf-8"))
        validate_public_content(topics, glossary)
    except (OSError, UnicodeError, json.JSONDecodeError, ValueError) as exc:
        raise SystemExit(f"Bundle rejected: {exc}") from exc

    target = ROOT / "content"
    target.mkdir(exist_ok=True)
    for name in sorted(EXPECTED):
        shutil.copyfile(bundle / name, target / name)
    print("Bundle imported. Run python3 scripts/validate_public.py before committing.")


if __name__ == "__main__":
    main()
