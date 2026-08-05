# LLM Notes

A public, installable, offline-capable knowledge base for machine learning and large language model systems.

## Architecture

```text
private source repository
├── private planning and source material
├── context-aware sensitive-content checks
└── privacy-reviewed chapter export
            │ explicit allowlist + manual review
            ▼
public llm-notes repository
├── 39 substantive HTML chapter fragments
├── neutral topic registry and glossary
├── strict structural and generic leak checks
├── generated static topic pages
├── installable web-app manifest
├── manual offline cache
└── GitHub Pages deployment
            ▼
iPhone Home Screen web app
```

The public repository never imports private Git history. The current chapter corpus contains approximately 698,000 text characters across 39 technical chapters.

## Public content model

- `content/topics.json`: neutral topic titles, summaries, prerequisites, and connections.
- `content/glossary.json`: concise technical definitions.
- `content/chapters/*.html`: privacy-reviewed substantive chapter fragments.
- `content/chapter-manifest.json`: SHA-256 hashes, character counts, and section counts for every chapter.
- `scripts/build_site.py`: deterministic static-site and PWA generator.
- `scripts/content_policy.py`: schema, chapter-integrity, generic leak, and optional secret-backed checks.
- `scripts/validate_public.py`: privacy, content-depth, link, and battery-behavior checks.
- `scripts/import_bundle.py`: fail-closed importer for reviewed chapter exports.
- `site/`: generated output; ignored locally and produced in CI.

## Local development

```bash
python3 scripts/build_site.py
python3 scripts/validate_public.py
python3 -m http.server 8000 --directory site
```

Then open `http://localhost:8000/`.

## Importing a privacy-reviewed chapter export

The importer accepts the private workflow artifact ZIP or its extracted directory. The export must contain exactly:

```text
topics.json
manifest.json
chapters/
  <39 topic-id>.html
```

The exported topic metadata must match the independently maintained public registry. Every chapter is checked against its hash, character count, section count, HTML structure, links, and privacy policy before it replaces `content/chapters/`.

```bash
python3 scripts/import_bundle.py /path/to/public-notes-export
python3 scripts/validate_public.py
```

The archive is only a transfer artifact. The public repository stores each chapter directly as an ordinary HTML file; no unpacking workflow is part of the deployed application.

## Optional secret-backed publication policy

Repository administrators may configure `PUBLICATION_DENYLIST_B64`, a base64-encoded UTF-8 JSON list of private regular-expression strings. The patterns remain outside the public repository and are applied during validation and deployment without being printed.

The private workspace remains responsible for primary context-aware sanitization. The secret-backed check is defense in depth.

## PWA and battery behavior

- The small application shell is cached during service-worker installation.
- The complete detailed library is downloaded only after an explicit tap.
- Cached files are served locally when available.
- Refreshing the full library is a manual action.
- There are no analytics, ads, polling timers, push notifications, WebSockets, periodic synchronization, or background synchronization.

## GitHub Pages

The deployment workflow validates the complete corpus before uploading only the generated `site/` directory.

```text
https://art-test-stack.github.io/llm-notes/
```

## iPhone installation

1. Open the deployed site in Safari.
2. Tap **Share**.
3. Tap **Add to Home Screen** and enable **Open as Web App**.
4. Open the installed app once while online.
5. Tap **Download all notes for offline use**.

Everything committed or deployed from this repository is public.
