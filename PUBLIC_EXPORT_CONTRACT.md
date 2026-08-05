# Public export contract

This repository is the public publication boundary for a separate private knowledge workspace. It accepts only a reviewed chapter export and does not import source history, attachments, planning files, or arbitrary directories.

## Allowed export

The importer accepts a ZIP artifact or its extracted directory containing exactly:

```text
topics.json
manifest.json
chapters/
  <topic-id>.html
```

There must be one chapter for each registered public topic and no additional files or directories. After validation, every chapter is stored directly under `content/chapters/`.

## Chapter requirements

Each source chapter must:

- be rooted at `<section class="chapter-content" data-topic="topic-id">`;
- contain at least 1,500 plain-text characters and three level-two sections;
- use only local fragment or topic links;
- contain no scripts, styles, embeds, forms, external assets, or executable URLs;
- contain no personal data, credentials, local paths, internal-network URLs, private navigation, or private provenance sections;
- match its SHA-256 hash, character count, section count, and equation count in `manifest.json`;
- preserve each explicitly marked formula as a `.math-inline` or `.math-display` element with a non-empty canonical `data-tex` attribute and readable fallback;
- contain no pre-rendered KaTeX or MathML before the public build.

The manifest uses schema version 2 and declares `total_math_expressions` plus `math_expressions` for every chapter.

## Reviewed formula-like code spans

Some legacy chapters used `<code>` for tensor shapes or mathematical formulas. The public repository may promote those spans only through `content/math-code-promotions.json`.

Each promotion must contain:

```json
{
  "text": "exact visible source text",
  "tex": "reviewed canonical TeX",
  "occurrences": 1
}
```

The renderer must fail when the exact source occurrence count changes. Generic pattern matching must not silently reinterpret arbitrary code as mathematics. Real configuration, program syntax, indexing expressions, and test conditions remain code.

## Mathematical publication boundary

The private exporter owns canonical mathematical source preservation. The public repository owns reviewed legacy classification and typesetting:

1. install the exact KaTeX version locked in `package-lock.json`;
2. verify every reviewed code promotion against exact visible source text and occurrence count;
3. render every preserved and promoted expression at build time with `output: "htmlAndMathml"`, `trust: false`, and parsing errors enabled;
4. ship KaTeX's static visual HTML together with its accessible MathML layer;
5. vendor the pinned KaTeX stylesheet and font files under `site/assets/katex/`;
6. fail when wrapper, visual-layer, accessibility-layer, native-MathML, or declared equation counts differ;
7. reject deployed `data-tex`, math CDNs, browser-side KaTeX runtimes, and auto-render scripts.

Long formulas must be constrained by local scroll containers so they cannot expand the document viewport. The service worker caches the stylesheet immediately and downloads the full local font set only with the explicit offline-library action.

## Explicit allowlist

Public exports may contain generic machine-learning theory, LLM architecture and systems material, probabilistic modelling, generative models, safety material, neutral technical relationships, equations, tables, pseudocode, and review questions.

Public exports must not contain personal identity or contact information, employment applications, recruiting communications, company-specific interview processes, unpublished role descriptions, private source filenames, personal schedules, compensation, referrals, credentials, internal URLs, or copied private Git history.

## Split privacy policy

Context-specific identifiers are checked and neutralized in the private exporter. They are not committed to this public repository, even inside denylist source code.

The public repository independently enforces exact schemas, hashes, chapter depth, canonical and promoted equation counts, local KaTeX assets, unique IDs, valid relationships, generic leak patterns, local-only links, and battery-safe PWA behavior. An optional `PUBLICATION_DENYLIST_B64` Actions secret provides defense in depth without exposing private patterns.

## Clean-history rule

Content is transferred only as newly generated files, never by forking, mirroring, merging, or copying commits from the private repository. Transfer archives and temporary diagnostic workflows are removed before a public pull request is finalized.

## Validation sequence

1. Generate the chapter export from the private allowlist.
2. Verify that every source math element has canonical TeX.
3. Run the private context-aware sanitizer and validation.
4. Manually inspect the artifact as public information.
5. Import it with `python3 scripts/import_bundle.py <bundle>`.
6. Review any formula-like code promotions explicitly.
7. Install locked build dependencies with `npm ci`.
8. Run `python3 scripts/validate_public.py`.
9. Inspect browser diagnostics for representative desktop and mobile pages when mathematical presentation changes.
10. Inspect the public pull-request diff.
11. Merge only after validation passes.

Ambiguous material is excluded. Adding a new public data type requires changing this contract, importer, and validator in the same reviewed pull request.
