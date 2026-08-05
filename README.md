# LLM Notes

A public, installable, offline-capable knowledge base for machine learning and large language model systems.

## Architecture

```text
private source repository
├── private planning and source material
├── context-aware sensitive-content checks
└── privacy-reviewed chapter export with canonical TeX
            │ explicit allowlist + manual review
            ▼
public llm-notes repository
├── 39 substantive HTML chapter fragments
├── 1,395 preserved TeX expressions
├── build-time KaTeX → native MathML rendering
├── neutral topic registry and glossary
├── strict structural and generic leak checks
├── installable web-app manifest
├── manual offline cache
└── GitHub Pages deployment
            ▼
iPhone Home Screen web app
```

The public repository never imports private Git history. Mathematical source is kept in `data-tex` attributes inside the reviewed chapter fragments and converted during the build to static MathML. The deployed site contains no KaTeX runtime, CDN dependency, or downloadable math font package.

## Public content model

- `content/topics.json`: neutral topic titles, summaries, prerequisites, and connections.
- `content/glossary.json`: concise technical definitions.
- `content/chapters/*.html`: privacy-reviewed chapter fragments with canonical TeX and readable fallbacks.
- `content/chapter-manifest.json`: SHA-256 hashes, character counts, section counts, and equation counts.
- `scripts/render_math.cjs`: pinned KaTeX server-side renderer producing MathML only.
- `scripts/build_site.py`: deterministic static-site and PWA generator.
- `scripts/content_policy.py`: schema, integrity, TeX, generic leak, and optional secret-backed checks.
- `scripts/validate_public.py`: privacy, content-depth, exact MathML-count, link, and battery-behavior checks.
- `package-lock.json`: reproducible KaTeX 0.18.1 build dependency.
- `site/`: generated output; ignored locally and produced in CI.

## Local development

```bash
npm ci --ignore-scripts --no-audit --no-fund
python3 scripts/build_site.py
python3 scripts/validate_public.py
python3 -m http.server 8000 --directory site
```

Then open `http://localhost:8000/`.

## Mathematical rendering

The private exporter preserves every equation as canonical TeX plus a plain-text fallback. During the public build:

1. `scripts/content_policy.py` verifies the declared TeX count and integrity hashes.
2. `scripts/render_math.cjs` calls `katex.renderToString` with `output: "mathml"`.
3. `scripts/build_site.py` embeds the resulting static MathML in each page.
4. `scripts/validate_public.py` requires exactly the manifest-declared number of `<math>` elements and rejects remaining `data-tex` attributes.

This makes equations readable online and offline without executing a mathematical renderer on the device.

## Importing a privacy-reviewed chapter export

The importer accepts the private workflow artifact ZIP or its extracted directory:

```text
topics.json
manifest.json
chapters/
  <39 topic-id>.html
```

```bash
python3 scripts/import_bundle.py /path/to/public-notes-export
npm ci --ignore-scripts --no-audit --no-fund
python3 scripts/validate_public.py
```

The archive is only a transfer artifact. The repository stores every chapter directly as an ordinary HTML file.

## Optional secret-backed publication policy

Repository administrators may configure `PUBLICATION_DENYLIST_B64`, a base64-encoded UTF-8 JSON list of private regular-expression strings. The patterns remain outside the public repository and are applied during validation and deployment without being printed.

## PWA and battery behavior

- The small application shell is cached during service-worker installation.
- The complete detailed library is downloaded only after an explicit tap.
- Equations arrive as static MathML; there is no browser-side KaTeX execution.
- Refreshing the full library is a manual action.
- There are no analytics, ads, polling timers, push notifications, WebSockets, periodic synchronization, or background synchronization.

## GitHub Pages

The deployment workflow installs the pinned build dependency, renders and validates the complete corpus, then uploads only `site/`.

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
