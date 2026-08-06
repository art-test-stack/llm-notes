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
├── 40 substantive HTML chapter fragments
├── 1,395 preserved canonical TeX expressions
├── 146 reviewed promotions of formula-like code spans
├── build-time KaTeX → static HTML + accessible MathML
├── local KaTeX stylesheet and fonts
├── neutral topic registry and glossary
├── installable web-app manifest
├── manual offline cache
└── GitHub Pages deployment
            ▼
iPhone Home Screen web app
```

The public repository never imports private Git history. Mathematical source is converted during the build to KaTeX's static visual HTML plus an accessibility MathML layer. The deployed site contains no KaTeX JavaScript runtime or external math dependency.

## Public content model

- `content/topics.json`: neutral topic titles, summaries, prerequisites, and connections.
- `content/glossary.json`: concise technical definitions.
- `content/chapters/*.html`: privacy-reviewed chapter fragments with canonical TeX and readable fallbacks.
- `content/chapter-manifest.json`: SHA-256 hashes, character counts, section counts, and canonical equation counts.
- `content/math-code-promotions.json`: explicit reviewed conversions for formula-like spans that were historically marked as code.
- `scripts/render_math.cjs`: pinned KaTeX build-time renderer producing static HTML and MathML.
- `scripts/build_site.py`: deterministic static-site and PWA generator that vendors KaTeX presentation assets.
- `scripts/content_policy.py`: schema, integrity, TeX, generic leak, and optional secret-backed checks.
- `scripts/validate_public.py`: privacy, exact equation-layer counts, local asset, link, and battery-behavior checks.
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

The pipeline separates source preservation, reviewed classification, and presentation:

1. The private exporter preserves canonical TeX for explicitly marked inline and display equations.
2. `content/math-code-promotions.json` explicitly classifies legacy formula-like `<code>` spans; no broad heuristic silently changes code into mathematics.
3. `scripts/render_math.cjs` renders every expression with KaTeX using `output: "htmlAndMathml"`, `trust: false`, and parse failures enabled.
4. `scripts/build_site.py` copies the pinned KaTeX stylesheet and font files into `site/assets/katex/`.
5. `scripts/validate_public.py` requires an exact one-to-one set of static wrappers, visual KaTeX layers, accessible MathML layers, and native `<math>` elements.
6. Chromium and WebKit diagnostics verify the reported desktop and iPhone pages without document-width overflow.

The current corpus publishes 1,541 typeset expressions: 1,395 canonical TeX expressions plus 146 reviewed promotions. Long display formulas remain inside horizontally scrollable local containers rather than expanding the whole page.

## Importing a privacy-reviewed chapter export

The importer accepts the private workflow artifact ZIP or its extracted directory:

```text
topics.json
manifest.json
chapters/
  <40 topic-id>.html
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

- The small application shell and local equation stylesheet are cached during service-worker installation.
- The complete detailed library and local KaTeX fonts are downloaded only after an explicit tap.
- Equations arrive as static HTML and MathML; there is no browser-side KaTeX execution.
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
