---
title: TIDAS SDKs
docType: guide
scope: repo
status: active
authoritative: false
owner: tidas-sdk
language: en
whenToUse:
  - when getting oriented to the tidas-sdk repository
  - when looking for package locations, setup commands, or verification entrypoints
whenToUpdate:
  - when package status, setup commands, generation flow, or verification entrypoints change
checkPaths:
  - README.md
  - AGENTS.md
  - docs/agents/repo-validation.md
  - docs/agents/repo-architecture.md
  - sdks/typescript/**
  - sdks/python/**
  - scripts/ci/**
  - .nvmrc
lastReviewedAt: 2026-10-18
lastReviewedCommit: 3c0b7eb4fab554418f7e71620146e65366a9d246
lastReviewedNote: "Reviewed SDK #168 after composing delivered #169: exact Actions pins and real Python artifact transfer retain the public Model/Process tests and 95/75/70 coverage gates; package graph, versions, runtime/source identities and release authority are unchanged."
---

# TIDAS SDKs

A multi-language SDK repository for TIDAS (TianGong Life Cycle Assessment data format), providing the generated TypeScript package, the in-repo Python SDK, and the automation that refreshes and releases them from the pinned `tidas-spec` archive plus `tidas-tools`.

## AI Docs Entry

For AI-first repo work, load docs in this order:

1. [AGENTS.md](./AGENTS.md)
2. [.docpact/config.yaml](./.docpact/config.yaml)
3. [docs/agents/repo-validation.md](./docs/agents/repo-validation.md) or [docs/agents/repo-architecture.md](./docs/agents/repo-architecture.md)
4. [docs/upstream-automation.md](./docs/upstream-automation.md) or [docs/release-setup.md](./docs/release-setup.md) when automation or publishing is part of the task

## Quick Start

### TypeScript SDK

```bash
pnpm add @tiangong-lca/tidas-sdk
```

### Python SDK (Development)

```bash
cd sdks/python && uv sync
```

### Upstream Tools

`tidas-tools` remains the native Rust upstream for execution-oriented generation helpers, product profiles, runtime rulesets, taxonomies, optional methodologies, and standalone tooling behavior. Public schemas, the schema lock, and public methodologies are consumed from one separately versioned, content-addressed `tidas-spec` archive. The package-input and public-rule pins bind the formal spec `0.3.0` release at `32e1ba38da7d5f4f6245c6c1927f83b326cd5404`, with exact archive and manifest hashes. TypeScript `0.5.0` and Python `0.3.0` adopt repeated fields, named classifications and canonical/legacy alias validation while retaining conditional Process references and required documentation. Product execution policy stays with its consumers; the former mixed `runtime_rulesets.json` and its schema are omitted from the SDK runtime projection without changing the upstream tools lock.

The TypeScript contracts entry point exposes `getTidasPublicRules(kind)` and `getTidasPublicRulesSchema()`. `getTidasPublicRules` returns an explicit `covered` or `not-covered` result with source identity; it never supplies severity, phase, blocker defaults, waivers, profiles, or action authorization. The former `getTidasRuntimeRuleset` compatibility API is removed; CLI owns the execution rules and AI context it derives from them.

```bash
cargo install tidas --locked
```

### Upstream release events

The sync workflow accepts two repository-dispatch contracts: `tidas_tools_changed` for execution-oriented inputs and `tidas_spec_released` for a reviewed immutable specification release. The latter must carry the exact package/version/source commit, canonical archive URL and filename, archive SHA256, manifest SHA256, an `event_key` of `package@version:archive_sha256:manifest_sha256`, and package/bump choices under `release_options`. The receiver verifies and downloads that archive before generation, replaces explicit candidate-only provenance when archive and manifest digests are unchanged, treats exact replays as no-ops, and rejects stale or same-version byte conflicts. The historical 0.2.0 candidate promotion remains the only reviewed byte-changing exception.

## Available Packages

### @tiangong-lca/tidas-sdk (TypeScript)

- Status: production package
- Features: type-safe data manipulation, validation, XML conversion, directory tools, and packaged runtime assets
- Installation: `pnpm add @tiangong-lca/tidas-sdk`
- Location: `sdks/typescript/`

### tidas-sdk (Python)

- Status: in development (pre-1.0)
- Features: generated Python models, validation helpers, and utilities
- Installation: `pip install tidas-sdk` (published on PyPI)
- Development: `cd sdks/python && uv sync` (see the Python SDK (Development) section above)
- Location: `sdks/python/`

### tidas-tools (External Upstream)

- Status: separate native Rust upstream
- Role: generation source, upstream schemas/assets, and standalone conversion / export tooling
- Repository: `tiangong-lca/tidas-toolkit`

### tidas-spec (External Upstream)

- Status: versioned public specification archive
- Role: public JSON Schemas, schema lock, and public methodology assets consumed by SDK generation
- Repository: `tiangong-lca/tidas-spec`

## Documentation

- Repository Contract: [AGENTS.md](./AGENTS.md)
- Validation Guide: [docs/agents/repo-validation.md](./docs/agents/repo-validation.md)
- Architecture Notes: [docs/agents/repo-architecture.md](./docs/agents/repo-architecture.md)
- Dependency Updates: [docs/agents/dependency-updates.md](./docs/agents/dependency-updates.md)
- Release Setup: [docs/release-setup.md](./docs/release-setup.md)
- Upstream Automation Design: [docs/upstream-automation.md](./docs/upstream-automation.md)
- TypeScript Release Guide: [sdks/typescript/RELEASE.md](./sdks/typescript/RELEASE.md)
- Python Release Guide: [sdks/python/RELEASE.md](./sdks/python/RELEASE.md)

Automated refresh PRs update the governed documentation review metadata together
with generated package files. Post-merge release detection also treats a current
package version without its expected repository tag as pending, so a governance
repair can recover an interrupted release without inventing a replacement version.

## Development

### Prerequisites

- TypeScript SDK: Node.js 24.19.0, pnpm 11.24.0
- Python SDK: Python 3.12+, uv

### Setup

#### TypeScript SDK

```bash
pnpm install --frozen-lockfile
pnpm --filter @tiangong-lca/tidas-sdk build
pnpm --filter @tiangong-lca/tidas-sdk test
```

#### Python SDK

```bash
cd sdks/python
uv sync
uv run pytest
uv run mypy .
```

#### Refresh Upstream TIDAS Sources

```bash
./scripts/ci/generate-typescript-sdk.sh
./scripts/ci/generate-python-sdk.sh
```

Both generation scripts resolve the exact `tidas-tools` commit declared by
`TIDAS_TOOLS_SHA` and the exact public archive declared by
`scripts/ci/tidas-spec-pin.json`:

1. `TIDAS_TOOLS_PATH`
2. a sibling checkout at `../tidas-toolkit`, then the pre-rename `../tidas-tools`
3. a temporary clone of `tiangong-lca/tidas-toolkit` checked out at that SHA

For `tidas-spec`, set `TIDAS_SPEC_ARCHIVE_PATH` to an explicit archive, use a
sibling `tidas-spec/release/` archive in auto mode, or let the resolver download
the pinned content-addressed URL. `scripts/ci/tidas-spec-assets.mjs` verifies the archive,
manifest, source evidence, and complete inventory before extraction. The same
verified spec identity is used for both language generators and the TypeScript
runtime assembly.

The generators validate every asset hash and byte count from
`assets/asset-lock.v1.json`. The TypeScript refresh derives its runtime roots
from that catalog, overlays the public paths from `tidas-spec`, and commits a
matching `runtime-assets/asset-lock.v1.json`;
it does not discover assets through the upstream Python package layout. When a
clean refresh needs generator dependencies, it requires the root
`pnpm-lock.yaml` and installs the complete workspace with
`pnpm install --frozen-lockfile`.

The TypeScript package uses a single `typescript@7.x` compiler track. Zod
schemas are generated directly from the locked JSON Schema assets, Oxlint owns
type-aware lint, and Node 24.19.0 owns the test runner. Packed consumers do not
inherit the compiler or generator toolchain.

### Release Workflow

Normal releases are tag-driven and published by GitHub Actions:

- TypeScript package: `typescript-vX.Y.Z`
- Python package: `python-vX.Y.Z`

Use these local verification commands before opening a release PR:

```bash
./scripts/ci/verify-typescript-package.sh
./scripts/ci/verify-python-package.sh
```

Except for validated branch-deletion-only pushes, the local `pre-push` hook runs docpact and then both verification scripts. The repository `CI` workflow also runs both verifiers at the exact head of main-target dependency/configuration/workflow PRs and remains manually dispatchable; package tags and publish workflows still verify the relevant package before release. See [Dependency Updates](docs/agents/dependency-updates.md) for monitoring and review boundaries.

If you want `tidas-tools` changes to automatically regenerate and release these packages, see [docs/upstream-automation.md](./docs/upstream-automation.md).

## Current Status

### Completed

- TypeScript SDK with committed schemas and runtime assets
- XML conversion and directory tooling for the non-export `tidas-tools` workflow
- Python SDK code generation and validation helpers
- Tag-driven release automation for TypeScript and Python packages

### In Progress

- Python SDK maturation and test coverage improvements
- cross-repository automation from `tidas-tools` into `tidas-sdk`

## Contributing

Review [AGENTS.md](./AGENTS.md) first for:

- repo boundaries
- validation expectations
- branch and delivery rules
- workspace integration expectations

TypeScript 0.6.0 prepares a versioned validation migration with exact Zod 4.6.7; see the [package migration guide](sdks/typescript/README.md#typescript-06-validation-migration). Python stays 0.3.0. Qualified local source/artifacts do not prove registry publication or upgrade any consumer.
