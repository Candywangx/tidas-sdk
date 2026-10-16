---
title: tidas-sdk Architecture Notes
docType: guide
scope: repo
status: active
authoritative: false
owner: tidas-sdk
language: en
whenToUse:
  - when you need a compact mental model of the repo before editing package code, generation scripts, or release automation
  - when deciding which package or automation layer owns a behavior change
  - when upstream sync, runtime assets, or release tags are mentioned without exact paths
whenToUpdate:
  - when package topology or generation flow changes
  - when new release automation makes the current map misleading
  - when stable versus generated paths move
checkPaths:
  - docs/agents/repo-architecture.md
  - .docpact/config.yaml
  - .nvmrc
  - scripts/ci/**
  - sdks/typescript/**
  - sdks/python/**
  - .github/workflows/**
  - .githooks/pre-push
  - scripts/docpact
  - scripts/docpact-gate.sh
  - scripts/install-git-hooks.sh
lastReviewedAt: 2026-10-16
lastReviewedCommit: 13ab657a2f6aa4afb9fba42d312d6247a4f1a0c1
lastReviewedNote: "Reviewed SDK #162: scoped dependency/configuration PRs reuse both canonical verifiers at exact heads; weekly npm/pip/Actions monitoring retains exact source pins, generated artifacts, dependency contracts and tag-driven publication."
related:
  - ../../AGENTS.md
  - ../../.docpact/config.yaml
  - ./repo-validation.md
  - ../upstream-automation.md
---

## Repo Shape

This repo packages two SDK surfaces under one root:

- `sdks/typescript/`
- `sdks/python/`

The root owns generation, verification, tagging, and publish automation.
It also owns the Node package graph through the exact Node `24.19.0` `.nvmrc`
pin, `pnpm-workspace.yaml`, the exact `pnpm@11.24.0` declaration, and the single
root `pnpm-lock.yaml`.

## Stable Vs Generated Paths

| Path group | Role |
| --- | --- |
| `pnpm-workspace.yaml`, `pnpm-lock.yaml` | stable TypeScript SDK and examples workspace topology plus frozen dependency graph |
| `scripts/ci/**` | stable generation, verify, tag, and publish helpers |
| `docs/release-setup.md` | stable release-environment contract |
| `docs/upstream-automation.md` | stable upstream-sync design contract |
| `sdks/typescript/src/**` | TypeScript package source, including generated types, schemas, and committed runtime assets |
| `sdks/typescript/scripts/**` | TypeScript generation and asset-sync helpers |
| `sdks/python/src/**` | Python SDK source and committed generated models |
| `sdks/python/scripts/**` | Python generation helpers |
| `sdks/python/tests/**` | Python SDK tests |
| `sdks/typescript/dist/**` | generated build output, useful for packaging checks but not the first edit surface |
| `sdks/python/dist/**` | generated build artifacts, useful for packaging checks but not the first edit surface |
| `sdks/python/htmlcov/**` | generated test coverage output, not a durable source path |

## Upstream Flow

The practical executable chain today is:

`tidas-spec + tidas-tools -> tidas-sdk`

The canonical GitHub repositories are `tiangong-lca/tidas-toolkit` and
`tiangong-lca/tidas-sdks`; workspace directories and published SDK package names
retain their existing names.

Important consequences:

- `scripts/ci/tidas-spec-assets.mjs` verifies the pinned public specification archive, its manifest, source evidence, and the exact public subset before exposing an asset root
- `scripts/ci/tidas-tools-assets.mjs` validates the execution-oriented Rust asset lock and derives runtime roots from catalog entries rather than package-layout assumptions
- `scripts/ci/lib/tidas-spec-source.sh` resolves one verified spec archive for the whole generation/verification process; schemas, the schema lock, and public `flows`/`processes` methodologies never fall back to `tidas-tools`
- a `tidas_spec_released` event refreshes the package-input pin and public-rule source identity from that same verified archive before regenerating TypeScript and Python; the public-rule index/schema bytes are copied from the archive even if their digests are unchanged
- `scripts/ci/lib/typescript-dependencies.sh` gives clean generation and verification runs the same `pnpm install --frozen-lockfile` dependency graph from the root `pnpm-lock.yaml`
- TypeScript runtime assets are assembled from two verified inputs: all 39 public paths come from one exact `tidas-spec` archive, while product profiles, newer runtime profiles, taxonomies, and optional methodologies remain catalog-selected `tidas-tools` inputs. The SDK lock is a byte-verifiable projection of the immutable upstream `asset-lock.v1.json` that omits only the former mixed `runtime_rulesets.json` and its schema. For the reviewed 0.2.0 candidate, 34 public paths remain byte-identical imports and five repository-authored paths (the Process/LCIA Method schemas in both languages plus the derived schema lock) are explicitly pinned and overlaid from spec.
- `getTidasPublicRules` is the versioned public-definition boundary and returns explicit covered/not-covered results; the former `getTidasRuntimeRuleset` compatibility boundary is removed, and consumer execution policy is not a public specification source
- Python generated models consume the same verified `tidas-spec` schema directory as TypeScript
- `tidas` remains important for public docs-site content, but it is not an SDK asset source
- `sync-from-tidas-tools.yml` accepts a content-addressed `tidas_spec_released` event in addition to `tidas_tools_changed`; the former updates the exact spec pin only after archive and manifest digest verification, and immutable replay/conflict rules are enforced by `update-tidas-spec-pin.py`

## Package Responsibilities

### TypeScript package

The TypeScript package owns developer-facing APIs plus packaged runtime assets and helpers for the non-export portion of the `tidas-tools` workflow.

It also owns the stable validation contract that downstream apps consume:

- generated schemas can emit custom Zod issues for localized-text checks
- `sdks/typescript/scripts/json-schema-to-zod.ts` renders the locked upstream JSON Schema AST directly, without the TypeScript Compiler API or an intermediate generated interface
- `sdks/typescript/scripts/generate-zod-schemas.ts` applies the small named domain overlays for custom validation codes, recursive `common:other`, CAS checks, required localized text, and the Flow name condition
- `sdks/typescript/src/core/validation/json-schema.ts` supplies browser/Node-compatible oneOf, conditional, dependency, tuple, and deep-unique semantics used by generated modules
- unsupported structural schema shapes fail generation; there is no permissive fallback schema
- `sdks/typescript/scripts/verify-zod-generation-parity.ts` compares a candidate generator against a previously built baseline with stable success and issue code/path signatures
- `sdks/typescript/src/core/config/ValidationConfig.ts` normalizes raw Zod issues into the `validationIssues` payload returned by `validateEnhanced()`
- downstream consumers should rely on normalized issue codes instead of parsing free-form error text when they need stable programmatic behavior

The package toolchain is intentionally single-track: `typescript@7.x` is the
only compiler, `pnpm@11.24.0` owns the root workspace and dependency graph,
Oxlint performs type-aware lint, and Node 24.19.0 plus `tsx` executes the test
suites.
The published package does not carry compiler, generator, lint, or test tooling
into downstream installations.

The direct renderer intentionally establishes the pre-1.0 `0.2.x`
compatibility boundary. Historical generated Zod schemas under-enforced parts
of the authoritative Draft-07 inputs; downstream `^0.1.x` consumers do not
receive those corrections automatically. Each consumer upgrades deliberately
and runs its own real data cases.

### Python package

The Python package owns generated SDK surfaces and validation helpers that are published separately from standalone `tidas-tools`.
Its generator consumes the explicitly resolved schema directory from the pinned
`tidas-spec` archive and preserves the
same type-aware Flow name condition in generated Pydantic models.

## Release Automation

The normal release path is:

1. verify package changes
2. merge to `main`
3. let automation create:
   - `typescript-v<version>`
   - `python-v<version>`
4. let publish workflows ship from the immutable tag after package verification

This release model is part of the repo architecture, not just a release checklist.

## Common Misreads

- `tidas` is not the immediate generation upstream for current SDK refreshes
- standalone conversion and export still belong in `tidas-tools`
- generated build outputs are not the only durable source of truth
- a merged child PR does not finish workspace delivery

## Local Docpact Push Gate

This repository has a versioned local `pre-push` hook under `.githooks/pre-push` that, except for validated branch-deletion-only pushes, delegates to `scripts/docpact-gate.sh` and then runs both package verification scripts. The gate resolves the CLI through `scripts/docpact`, so local agent shells do not need bare `docpact` on `PATH`. The hook remains the local guard for docpact config validation, enforced doc-governance linting, and package tests. GitHub `CI` also runs the same package verifiers at exact PR heads for main-target dependency/configuration/workflow changes and remains manually dispatchable; [the dependency guide](dependency-updates.md) owns monitoring and review details.


The ILCD compatibility candidate extends generated singletons with repeated fields and named classifications. The Zod generator treats `$comment` as an annotation and supports the narrowly defined `not`/`required` form used for conflicting aliases; unsupported negation remains a generation error. TypeScript array generation groups union and intersection item types before appending `[]`. Platform policy, including review eligibility and deliberately required documentation, is not relaxed by these public shape changes.

## Process semantic analysis

`sdks/typescript/src/core/validation/process-semantics.ts` owns pure allocation/reference analysis and is exported from both root and `core`. It uses explicit exact Flow evidence, returns coverage and interpretations, and never participates implicitly in schema generation or `strict` validation. The TypeScript/Toolkit conformance fixture binds the versioned consumer policy; it is not a public specification asset. Consumers own resolver access, evidence hashes, modelling decisions and acceptance disposition.
