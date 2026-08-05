# LLM Notes

A public, installable, offline-capable knowledge base for machine learning and large language model systems.

## Architecture

```text
private source repository
├── private planning and source material
├── context-aware sensitive-content checks
└── privacy-reviewed export bundle
            │ explicit allowlist + manual review
            ▼
public llm-notes repository
├── content/topics.json
├── content/glossary.json
├── strict structural and generic leak checks
├── generated static topic pages
├── installable web-app manifest
├── manual offline cache
└── GitHub Pages deployment
            ▼
iPhone Home Screen web app
```

The public repository has a clean history and never imports commits from a private source. Only a reviewed two-file content bundle is accepted.

Context-specific sensitive names are deliberately **not committed here**, including inside validation denylist source code. They are checked in the private exporter. The public side enforces exact schemas and generic leak patterns, with an optional secret-backed denylist for defense in depth.

## Public content model

- `content/topics.json`: neutral topic metadata, summaries, prerequisites, and connections.
- `content/glossary.json`: concise technical definitions.
- `scripts/build_site.py`: deterministic static-site and PWA generator.
- `scripts/content_policy.py`: structural schema, generic leak detection, and optional secret policy.
- `scripts/validate_public.py`: privacy, link, and battery-behavior checks.
- `scripts/import_bundle.py`: fail-closed importer for reviewed bundles.
- `site/`: generated output; ignored locally and produced in CI.

## Local development

```bash
python3 scripts/build_site.py
python3 scripts/validate_public.py
python3 -m http.server 8000 --directory site
```

Then open `http://localhost:8000/`.

## Importing a privacy-reviewed bundle

The bundle must contain exactly:

```text
topics.json
glossary.json
```

Import and validate it with:

```bash
python3 scripts/import_bundle.py /path/to/export-bundle
python3 scripts/validate_public.py
```

## Optional secret-backed publication policy

Repository administrators may configure the Actions secret `PUBLICATION_DENYLIST_B64`. It is a base64-encoded UTF-8 JSON list of private regular-expression strings. The patterns remain outside the repository and are applied during validation and deployment without being printed.

The private workspace remains responsible for the primary context-aware review. This optional secret is only defense in depth.

## PWA and battery behavior

- The small application shell is cached during service-worker installation.
- The complete note library is downloaded only after an explicit tap.
- Cached files are served locally when available.
- Refreshing the full library is a manual action.
- There are no analytics, ads, polling timers, push notifications, WebSockets, periodic synchronization, or background synchronization.

## GitHub Pages

After this PR is merged, configure the repository under **Settings → Pages → Source → GitHub Actions**. The deployment workflow builds and validates the public site before uploading only the generated `site/` directory.

Expected project URL:

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
