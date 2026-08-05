# Public export contract

This repository is the public publication boundary for a separate private knowledge workspace. It accepts only a reviewed chapter export and does not import source history, attachments, planning files, or arbitrary directories.

## Allowed export

The importer accepts a ZIP artifact or its extracted directory. Its contents must be exactly:

```text
topics.json
manifest.json
chapters/
  <topic-id>.html
```

There must be exactly one chapter for each of the 39 registered public topics and no additional files or directories. After validation, the public repository stores every chapter directly under `content/chapters/` as an ordinary HTML file.

## Exported topic schema

Each exported topic contains exactly:

```json
{
  "id": "stable-kebab-case-id",
  "title": "Neutral technical title",
  "track": "Technical category",
  "prerequisites": ["topic-id"],
  "connections": ["topic-id"],
  "chapter": "chapters/topic-id.html"
}
```

These fields must match the independently maintained public topic registry. Public summaries remain in `content/topics.json`.

## Chapter requirements

Each chapter must:

- be a self-contained HTML fragment rooted at `<section class="chapter-content" data-topic="topic-id">`;
- contain at least 1,500 plain-text characters and at least three level-two sections;
- use only local fragment or topic links;
- contain no scripts, styles, embeds, forms, external assets, or executable URLs;
- contain no personal data, credentials, local paths, internal-network URLs, private navigation, or private provenance sections;
- match the SHA-256 hash, character count, and section count in `manifest.json`.

## Explicit allowlist

Public exports may contain generic machine-learning theory, LLM architecture and systems material, probabilistic modelling, generative models, safety material, neutral technical relationships, equations, tables, pseudocode, and review questions.

Public exports must not contain personal identity or contact information, employment applications, recruiting communications, company-specific interview processes, unpublished role descriptions, private source filenames, personal schedules, compensation, referrals, credentials, internal URLs, or copied private Git history.

## Split privacy policy

Context-specific identifiers are checked and neutralized in the private exporter. They are not committed to this public repository, even inside denylist source code.

The public repository independently enforces exact schemas, hashes, chapter depth, unique IDs, valid relationships, generic leak patterns, local-only links and assets, and battery-safe PWA behavior. An optional `PUBLICATION_DENYLIST_B64` Actions secret provides defense in depth without exposing private patterns.

## Clean-history rule

Content is transferred only as newly generated files, never by forking, mirroring, merging, or copying commits from the private repository. The transfer archive is not retained in the final public tree.

## Validation sequence

1. Generate the chapter export from the private allowlist.
2. Run the private context-aware sanitizer and validation.
3. Manually inspect the artifact as public information.
4. Import it with `python3 scripts/import_bundle.py <bundle>`.
5. Run `python3 scripts/validate_public.py`.
6. Inspect the public pull-request diff.
7. Merge only after validation passes.

Ambiguous material is excluded. Adding a new public data type requires changing this contract, importer, and validator in the same reviewed pull request.
