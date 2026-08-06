#!/usr/bin/env python3
from __future__ import annotations

import os
import sys
from pathlib import Path


def append_summary(message: str) -> None:
    summary = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary:
        with Path(summary).open("a", encoding="utf-8") as handle:
            handle.write(message + "\n")


def main() -> None:
    encoded = os.environ.get("PUBLICATION_DENYLIST_B64", "").strip()
    required = os.environ.get("REQUIRE_PUBLICATION_DENYLIST", "0") == "1"
    if encoded:
        message = "Private publication denylist is configured."
        print(message)
        append_summary(f"✅ {message}")
        return
    message = "PRIVATE PUBLICATION DENYLIST IS NOT CONFIGURED."
    append_summary(f"⚠️ {message}")
    if required:
        raise SystemExit(message + " Refusing to build a deployable artifact.")
    print("::warning::" + message, file=sys.stderr)


if __name__ == "__main__":
    main()
