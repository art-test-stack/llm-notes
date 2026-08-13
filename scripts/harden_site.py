#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import os
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SITE = ROOT / "site"
VERSION_RE = re.compile(r'const V="[^"]+"')
INSTALL_OLD = 'self.addEventListener("install",e=>e.waitUntil(caches.open(S).then(c=>c.addAll(CORE))));'
INSTALL_NEW = 'self.addEventListener("install",e=>e.waitUntil(caches.open(S).then(c=>c.addAll(CORE)).then(()=>self.skipWaiting())));'


def project_name() -> str:
    repository = os.environ.get("GITHUB_REPOSITORY", "art-test-stack/llm-notes")
    return repository.rsplit("/", 1)[-1]


def write_self_contained_404(site: Path) -> None:
    project = project_name()
    page = f'''<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">
<meta name="theme-color" content="#172554">
<title>Page not found · LLM Notes</title>
<style>
:root{{color-scheme:light dark;font-family:Inter,-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif}}
*{{box-sizing:border-box}}
body{{margin:0;min-height:100vh;display:grid;place-items:center;padding:24px;background:#f8fafc;color:#172033}}
main{{width:min(620px,100%);padding:clamp(28px,7vw,64px);border:1px solid #cbdcf8;border-radius:24px;background:#fff;box-shadow:0 18px 50px rgba(15,23,42,.10)}}
h1{{margin:.2rem 0 1rem;font-size:clamp(2rem,7vw,3.6rem);line-height:1.05}}
p{{color:#5b6474;line-height:1.65}}
a{{display:inline-flex;min-height:44px;align-items:center;margin-top:14px;padding:10px 16px;border-radius:12px;background:#172554;color:#fff;font-weight:750;text-decoration:none}}
@media(prefers-color-scheme:dark){{body{{background:#0b1120;color:#e5e7eb}}main{{background:#111827;border-color:#263b65}}p{{color:#a8b0bf}}a{{background:#dbeafe;color:#172554}}}}
</style>
</head>
<body>
<main>
<p>LLM Notes</p>
<h1>Page not found</h1>
<p>The requested page does not exist or may have moved.</p>
<a id="home" href="/">Open LLM Notes</a>
</main>
<script>
(()=>{{
  const project={project!r};
  const marker="/"+project+"/";
  const root=location.pathname.startsWith(marker)?marker:"/";
  document.getElementById("home").href=root+"index.html";
}})();
</script>
</body>
</html>
'''
    (site / "404.html").write_text(page, encoding="utf-8")


def content_digest(site: Path) -> str:
    digest = hashlib.sha256()
    for path in sorted(site.rglob("*")):
        if not path.is_file() or path.name == "service-worker.js":
            continue
        relative = path.relative_to(site).as_posix().encode("utf-8")
        digest.update(len(relative).to_bytes(4, "big"))
        digest.update(relative)
        data = path.read_bytes()
        digest.update(len(data).to_bytes(8, "big"))
        digest.update(data)
    return digest.hexdigest()[:16]


def harden_service_worker(site: Path) -> str:
    path = site / "service-worker.js"
    source = path.read_text(encoding="utf-8")
    version = content_digest(site)
    source, replacements = VERSION_RE.subn(f'const V="{version}"', source, count=1)
    if replacements != 1:
        raise RuntimeError("Could not replace the service-worker cache version")
    if INSTALL_OLD not in source:
        raise RuntimeError("Unexpected service-worker install handler")
    source = source.replace(INSTALL_OLD, INSTALL_NEW, 1)
    path.write_text(source, encoding="utf-8")
    return version


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--site", type=Path, default=DEFAULT_SITE)
    args = parser.parse_args()
    site = args.site.resolve()
    if not site.is_dir():
        raise SystemExit(f"Generated site does not exist: {site}")
    write_self_contained_404(site)
    version = harden_service_worker(site)
    print(f"Hardened generated site with content-derived cache version {version}.")


if __name__ == "__main__":
    main()
