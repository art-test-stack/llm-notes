#!/usr/bin/env python3
from __future__ import annotations

import argparse
import base64
import html
import json
import shutil
from pathlib import Path

from app_assets import APP, CSS, FILTER, SVG, SW
from icons import ICON_180, ICON_192, ICON_512

ROOT = Path(__file__).resolve().parents[1]
CONTENT = ROOT / "content"
SITE = ROOT / "site"

TRACK_HINTS = {
    "Data": "Focus on representation, lineage, distribution shifts, and reproducibility.",
    "Applied LLM": "Separate retrieval or orchestration quality from generation quality and system behavior.",
    "Inference": "Reason about latency, memory traffic, cache state, batching, and correctness under real request shapes.",
    "Systems": "Start from placement, communication, synchronization, topology, and failure recovery.",
    "Architecture": "Track tensor shapes, information flow, computational complexity, and inductive bias.",
    "Post-training": "State the feedback source, objective, reference policy, and evaluation boundary.",
    "Evaluation": "Define the decision, distribution, slices, uncertainty, and operational acceptance criteria.",
    "Agents": "Keep model proposals separate from validation, authorization, execution, and durable state.",
    "Efficiency": "Measure end-to-end effects on the target hardware rather than relying on nominal reductions.",
    "Safety": "Model trust boundaries, capabilities, authorization, data exposure, and adversarial inputs.",
    "Training": "Connect empirical scaling assumptions to actual data, hardware, and optimizer behavior.",
    "Probabilistic foundations": "State random variables, measures, factorization assumptions, and the inference target.",
    "Bayesian inference and uncertainty": "Distinguish uncertainty source, approximation, calibration, and decision use.",
    "Stochastic processes and sequential models": "Separate latent dynamics, observations, inference direction, and numerical approximation.",
    "Generative modelling": "Specify the probability path, training target, sampling dynamics, and evaluation regime.",
    "Path-based modelling": "Specify interpolation, invariances, truncation, and online versus offline assumptions.",
}


def esc(value: object) -> str:
    return html.escape(str(value), quote=True)


def load(name: str):
    return json.loads((CONTENT / name).read_text(encoding="utf-8"))


def page(title: str, body: str, depth: int = 0) -> str:
    prefix = "../" * depth
    return f'''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover"><meta name="theme-color" content="#172554"><title>{esc(title)} · LLM Notes</title><link rel="manifest" href="{prefix}manifest.webmanifest"><link rel="apple-touch-icon" href="{prefix}icons/apple-touch-icon.png"><link rel="stylesheet" href="{prefix}assets/styles.css"></head><body><header class="topbar"><a class="brand" href="{prefix}index.html">LLM Notes</a><nav><a href="{prefix}topics/index.html">Topics</a><a href="{prefix}glossary/index.html">Glossary</a><a href="{prefix}privacy.html">Privacy</a></nav></header>{body}<footer><p>Static public notes. No analytics, polling, push, or background synchronization.</p><p><button class="link-button" data-download>Download all notes for offline use</button> <span class="status" data-status></span></p></footer><script src="{prefix}assets/app.js" defer></script></body></html>'''


def links(ids: list[str], by_id: dict[str, dict]) -> str:
    if not ids:
        return "<p>None.</p>"
    return "<ul>" + "".join(
        f'<li><a href="{esc(topic_id)}.html">{esc(by_id[topic_id]["title"])}</a></li>'
        for topic_id in ids
    ) + "</ul>"


def card(topic: dict, depth: int = 0) -> str:
    prefix = "../" * depth
    searchable = (topic["title"] + " " + topic["track"] + " " + topic["summary"]).lower()
    return f'<article class="card" data-item data-group="{esc(topic["track"])}" data-text="{esc(searchable)}"><span class="eyebrow">{esc(topic["track"])}</span><h2><a href="{prefix}topics/{esc(topic["id"])}.html">{esc(topic["title"])}</a></h2><p>{esc(topic["summary"])}</p></article>'


def write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def build() -> None:
    if SITE.exists():
        shutil.rmtree(SITE)
    topics = load("topics.json")
    glossary = load("glossary.json")
    by_id = {topic["id"]: topic for topic in topics}
    tracks = sorted({topic["track"] for topic in topics})
    for topic in topics:
        for relation in topic["prerequisites"] + topic["connections"]:
            if relation not in by_id:
                raise SystemExit(f'{topic["id"]}: unknown relation {relation}')

    home = f'''<main><section class="hero"><p class="eyebrow">Public technical knowledge base</p><h1>Machine learning and LLM systems notes for focused reading.</h1><p class="lede">Browse {len(topics)} concise chapters across {len(tracks)} tracks. Install on iPhone and explicitly download the library once for low-battery offline reading.</p><div class="actions"><a class="button primary" href="topics/index.html">Browse topics</a><a class="button" href="glossary/index.html">Open glossary</a></div></section><section><h2>Privacy and battery by design</h2><div class="grid"><article class="card"><h2>Public-only content</h2><p>Only neutral technical notes and definitions are published.</p></article><article class="card"><h2>Manual offline download</h2><p>The full library is cached only after an explicit tap.</p></article><article class="card"><h2>No background activity</h2><p>No analytics, notifications, polling, or periodic synchronization.</p></article></div></section></main>'''
    write(SITE / "index.html", page("Home", home))

    options = "".join(f'<option>{esc(track)}</option>' for track in tracks)
    body = f'''<main class="page"><p class="eyebrow">Topic library</p><h1>All technical notes</h1><div class="toolbar"><label>Search<input data-search type="search" placeholder="e.g. KV cache or diffusion"></label><label>Track<select data-track><option value="">All tracks</option>{options}</select></label></div><p data-count class="status"></p><div class="grid">{"".join(card(topic, 1) for topic in topics)}</div></main><script src="../assets/filter.js" defer></script>'''
    write(SITE / "topics/index.html", page("Topics", body, 1))

    for topic in topics:
        hint = TRACK_HINTS.get(topic["track"], "Connect definitions, assumptions, implementation, and evaluation.")
        body = f'''<main class="article-layout"><article class="article"><p class="eyebrow">{esc(topic["track"])}</p><h1>{esc(topic["title"])}</h1><p class="lede">{esc(topic["summary"])}</p><section><h2>Study frame</h2><p>{esc(hint)}</p></section><section><h2>Questions to answer</h2><ul><li>What is the core mathematical or systems abstraction?</li><li>Which assumptions make the method valid or efficient?</li><li>What changes between training and deployment?</li><li>Which measurements would reveal failure?</li></ul></section></article><aside class="related"><h2>Prerequisites</h2>{links(topic["prerequisites"], by_id)}<h2>Connected topics</h2>{links(topic["connections"], by_id)}</aside></main>'''
        write(SITE / f'topics/{topic["id"]}.html', page(topic["title"], body, 1))

    definitions = "".join(
        f'<article class="definition" id="{esc(entry["id"])}" data-item data-group="" data-text="{esc((entry["term"] + " " + entry["definition"]).lower())}"><h2>{esc(entry["term"])}</h2><p>{esc(entry["definition"])}</p></article>'
        for entry in glossary
    )
    body = f'''<main class="page"><p class="eyebrow">Technical glossary</p><h1>{len(glossary)} concise definitions</h1><div class="toolbar"><label>Search<input data-search type="search" placeholder="e.g. ELBO or all-reduce"></label></div><p data-count class="status"></p>{definitions}</main><script src="../assets/filter.js" defer></script>'''
    write(SITE / "glossary/index.html", page("Glossary", body, 1))

    privacy = '''<main class="page"><p class="eyebrow">Privacy</p><h1>Public content, minimal device activity</h1><div class="privacy-box"><p>Everything deployed here is public and limited to generic technical notes.</p></div><section><h2>No collection</h2><ul><li>No analytics, accounts, cookies, ads, or fingerprinting.</li><li>No location, contacts, photos, microphone, or notification access.</li><li>No background synchronization or periodic refresh.</li></ul></section><section><h2>Offline storage</h2><p>The app shell is cached automatically. The full library is cached only after you tap the download control. Safari may evict web storage under device pressure.</p><button class="button" data-refresh>Refresh cached library</button></section></main>'''
    write(SITE / "privacy.html", page("Privacy", privacy))
    write(SITE / "offline.html", page("Offline", '<main class="page"><h1>This page is not cached yet.</h1><p>Reconnect once and use the offline download control.</p><a class="button primary" href="index.html">Return home</a></main>'))
    write(SITE / "404.html", page("Not found", '<main class="page"><h1>Page not found</h1><a class="button primary" href="index.html">Open LLM Notes</a></main>'))

    write(SITE / "assets/styles.css", CSS)
    write(SITE / "assets/app.js", APP)
    write(SITE / "assets/filter.js", FILTER)
    write(SITE / "service-worker.js", SW)
    write(SITE / "icons/icon.svg", SVG)
    (SITE / "icons").mkdir(parents=True, exist_ok=True)
    for name, data in [("apple-touch-icon.png", ICON_180), ("icon-192.png", ICON_192), ("icon-512.png", ICON_512)]:
        (SITE / "icons" / name).write_bytes(base64.b64decode(data))

    manifest = {
        "name": "LLM Notes",
        "short_name": "LLM Notes",
        "description": "Public technical notes on machine learning and LLM systems.",
        "id": "./",
        "start_url": "./index.html",
        "scope": "./",
        "display": "standalone",
        "background_color": "#f8fafc",
        "theme_color": "#172554",
        "icons": [
            {"src": "icons/icon-192.png", "sizes": "192x192", "type": "image/png"},
            {"src": "icons/icon-512.png", "sizes": "512x512", "type": "image/png", "purpose": "any maskable"},
        ],
    }
    write(SITE / "manifest.webmanifest", json.dumps(manifest, indent=2) + "\n")
    public_topics = [{**topic, "path": f'topics/{topic["id"]}.html'} for topic in topics]
    write(SITE / "data/topics.json", json.dumps(public_topics, ensure_ascii=False, indent=2) + "\n")
    write(SITE / "data/glossary.json", json.dumps(glossary, ensure_ascii=False, indent=2) + "\n")
    library = ["topics/index.html", "glossary/index.html", "privacy.html"] + [f'topics/{topic["id"]}.html' for topic in topics]
    write(SITE / "precache-library.json", json.dumps(library, indent=2) + "\n")
    write(SITE / ".nojekyll", "")
    print(f"Built {len(topics)} topic pages and {len(glossary)} definitions in {SITE}")


if __name__ == "__main__":
    argparse.ArgumentParser().parse_args()
    build()
