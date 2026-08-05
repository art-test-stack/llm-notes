# Public export contract

This repository is the public publication boundary for a separate private knowledge workspace. It accepts only a deliberately small, reviewed content bundle and does not import source history, attachments, planning files, or arbitrary directories.

## Allowed bundle

An import bundle must contain exactly two UTF-8 JSON files:

```text
topics.json
glossary.json
```

No subdirectories, HTML files, archives, images, logs, reports, or source documents are accepted.

## Topic schema

Each topic must contain exactly:

```json
{
  "id": "stable-kebab-case-id",
  "title": "Neutral technical title",
  "track": "Technical category",
  "summary": "Self-contained public summary",
  "prerequisites": ["topic-id"],
  "connections": ["topic-id"]
}
```

Topic IDs must be unique. Every prerequisite and connection must resolve to another exported topic.

## Glossary schema

Each glossary entry contains:

```json
{
  "id": "stable-kebab-case-id",
  "term": "Canonical technical term",
  "definition": "Concise public definition"
}
```

Glossary IDs and canonical terms must be unique.

## Explicit allowlist

Public exports may contain:

- generic machine-learning theory;
- generic LLM architecture, training, inference, evaluation, retrieval, and safety material;
- probabilistic modelling and generative-model concepts;
- neutral study relationships between technical topics;
- concise technical definitions.

Public exports must not contain:

- personal identity or contact information;
- employment applications or recruiting communications;
- company-specific interview processes or preparation strategy;
- unpublished role descriptions or private source documents;
- personal schedules, compensation, referrals, or application status;
- project claims that expose confidential context;
- credentials, tokens, internal URLs, or access instructions;
- copied repository history from a private source.

## Split privacy policy

Context-specific sensitive names must not be committed to this public repository, even inside a denylist. They are checked before export in the private workspace.

The public repository independently enforces:

- exact file and JSON schemas;
- unique IDs and valid topic relationships;
- absence of email addresses, local user paths, credential-shaped tokens, internal-network URLs, and executable markup;
- local-only runtime assets and battery-safe PWA behavior.

For defense in depth, repository administrators may define the optional Actions secret `PUBLICATION_DENYLIST_B64`. It must contain base64-encoded UTF-8 JSON representing a non-empty list of regular-expression strings. Validation reports only the pattern number and file location; it never prints the secret pattern or matching text.

## Clean-history rule

The public repository must remain independent. Content is transferred only as newly generated JSON data, never by forking, mirroring, merging, or copying commits from a private repository.

## Validation sequence

Before publication:

1. generate the two-file bundle from an explicit allowlist in the private workspace;
2. run the private context-aware review there;
3. manually review the resulting JSON files;
4. import with `python3 scripts/import_bundle.py <bundle>`;
5. run `python3 scripts/validate_public.py`;
6. inspect the pull-request diff as public information;
7. merge only after validation passes.

## Fail-closed behavior

Ambiguous material is excluded. Adding a new public data type requires changing this contract, the importer, and the validator in the same reviewed pull request.
