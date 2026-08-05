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
- preserve each formula as a `.math-inline` or `.math-display` element with a non-empty canonical `data-tex` attribute and a readable text fallback;
- contain no pre-rendered MathML before the public build.

The manifest uses schema version 2 and declares `total_math_expressions` plus `math_expressions` for every chapter.

## Mathematical publication boundary

The private exporter owns mathematical source preservation. It must recognize both inline `<span>` and display `<div>` math elements and preserve their canonical TeX.

The public build owns typesetting:

1. install the exact KaTeX version locked in `package-lock.json`;
2. render every preserved expression at build time with `output: "mathml"`, `trust: false`, and parsing errors enabled;
3. replace every source math element with static MathML;
4. fail when the rendered count differs from the manifest;
5. reject any deployed `data-tex` attribute, math CDN, browser-side KaTeX runtime, or auto-render script.

The browser receives native MathML only. KaTeX, its CSS, and its fonts are build dependencies rather than runtime dependencies.

## Explicit allowlist

Public exports may contain generic machine-learning theory, LLM architecture and systems material, probabilistic modelling, generative models, safety material, neutral technical relationships, equations, tables, pseudocode, and review questions.

Public exports must not contain personal identity or contact information, employment applications, recruiting communications, company-specific interview processes, unpublished role descriptions, private source filenames, personal schedules, compensation, referrals, credentials, internal URLs, or copied private Git history.

## Split privacy policy

Context-specific identifiers are checked and neutralized in the private exporter. They are not committed to this public repository, even inside denylist source code.

The public repository independently enforces exact schemas, hashes, chapter depth, TeX and MathML counts, unique IDs, valid relationships, generic leak patterns, local-only links and assets, and battery-safe PWA behavior. An optional `PUBLICATION_DENYLIST_B64` Actions secret provides defense in depth without exposing private patterns.

## Clean-history rule

Content is transferred only as newly generated files, never by forking, mirroring, merging, or copying commits from the private repository. Transfer archives and temporary materialization workflows are removed before a public pull request is finalized.

## Validation sequence

1. Generate the chapter export from the private allowlist.
2. Verify that every math element has canonical TeX.
3. Run the private context-aware sanitizer and validation.
4. Manually inspect the artifact as public information.
5. Import it with `python3 scripts/import_bundle.py <bundle>`.
6. Install locked build dependencies with `npm ci`.
7. Run `python3 scripts/validate_public.py`.
8. Inspect the public pull-request diff.
9. Merge only after validation passes.

Ambiguous material is excluded. Adding a new public data type requires changing this contract, importer, and validator in the same reviewed pull request.
