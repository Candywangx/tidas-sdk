---
title: tidas-sdk Repo Contract
docType: contract
scope: repo
status: active
authoritative: true
owner: tidas-sdk
language: en
whenToUse:
  - when a task may change generated TypeScript or Python SDK surfaces, package release automation, or the upstream-refresh workflow
  - when routing work from the workspace root into tidas-sdk
  - when deciding whether a change belongs here, in tidas-tools, in tidas, or in lca-workspace
whenToUpdate:
  - when package ownership or upstream-generation rules change
  - when release or verification scripts change
  - when repo-local documentation governance changes
checkPaths:
  - AGENTS.md
  - README.md
  - .docpact/**/*.yaml
  - docs/agents/**
  - docs/release-setup.md
  - docs/upstream-automation.md
  - .nvmrc
  - package.json
  - scripts/ci/**
  - sdks/typescript/**
  - sdks/python/**
  - .github/workflows/**
  - .githooks/**
  - scripts/docpact
  - scripts/docpact-gate.sh
  - scripts/install-git-hooks.sh
lastReviewedAt: 2026-10-18
lastReviewedCommit: 8849b1deb335cb326a3cd94083c59de71988ffc0
lastReviewedNote: "Reviewed SDK #171: TypeScript 0.6.0/exact Zod 4.6.7 prepares public-spec code-point/seconds validation and matching string diagnostics; Python/upstream assets, overlays, 95/75/70 gates and release automation are unchanged. Main merge/publication authorization remains separate."
related:
  - .docpact/config.yaml
  - docs/agents/repo-validation.md
  - docs/agents/repo-architecture.md
  - docs/release-setup.md
  - docs/upstream-automation.md
  - README.md
---

## Repo Contract

`tidas-sdk` owns the generated developer package surface for TIDAS: the published TypeScript package, the in-repo Python SDK, and the generation / verification / release automation that keeps them aligned with the standalone public `tidas-spec` archive and the execution-oriented `tidas-tools` asset set.

TypeScript 0.6.0 pins Zod 4.6.7 and uses public-spec Unicode code-point string bounds and RFC 3339 seconds. Normalized string actualLength uses code points; array diagnostics retain element counts. The package README owns migration details, including published 0.5.1's permissive transitive Zod range. Python remains 0.3.0.

For the TypeScript package, that ownership now includes the machine-readable validation contract exposed by `validateEnhanced()`: downstream callers should expect a stable `validationIssues` array with normalized `code`, `path`, `severity`, optional `params`, and `rawCode`, rather than parsing raw Zod messages when stable behavior matters.

The TypeScript SDK also owns `analyzeProcessSemantics()` as a separate, non-mutating consumer-policy API for allocation/reference interpretation, with exact caller-supplied Flow evidence and explicit per-check coverage. Structural `strict` validation and generated public schemas remain unchanged. Its versioned policy is documented in the TypeScript package README.

The TypeScript SDK publishes spec-owned public definitions but no longer exports the former mixed runtime-ruleset getter or bundles its two legacy files. Its derived runtime lock preserves the verified upstream tools-lock identity while excluding those exact files. Consumer execution policy remains outside the SDK; Python's package boundary is unchanged.

## Documentation Roles

| Document | Owns | Does not own |
| --- | --- | --- |
| `AGENTS.md` | repo contract, branch and delivery rules, hard boundaries, minimal execution facts | full path map, proof matrix, or long setup prose |
| `.docpact/config.yaml` | machine-readable repo facts, routing intents, governed-doc rules, ownership, coverage, and freshness | explanatory prose or long-form walkthroughs |
| `docs/agents/repo-validation.md` | minimum proof by change type, upstream-resolution notes, PR validation note shape | repo contract, branch policy truth, or topology explanations |
| `docs/agents/repo-architecture.md` | compact repo shape, stable path map, upstream flow, release model, and common misreads | checklist-style proof guidance or operator setup commands |
| `docs/release-setup.md` | registry setup, release environment, trusted publishing, and release workflow prerequisites | path ownership, routing semantics, or package topology |
| `docs/upstream-automation.md` | cross-repo automation design for `tidas-tools -> tidas-sdk` refreshes | current package validation baseline or branch-policy truth |
| `README.md` | repo landing context, package overview, basic setup commands, and AI docs entry | machine-readable routing or lint semantics |

## Load Order

Read in this order:

1. `AGENTS.md`
2. `.docpact/config.yaml`
3. `docs/agents/repo-validation.md` or `docs/agents/repo-architecture.md`
4. `docs/upstream-automation.md` or `docs/release-setup.md` only when automation or publishing is part of the task
5. package-local docs under `sdks/typescript/**` or `sdks/python/**` only when the task is already narrowed to one package surface

## Operational Pointers

- path-level ownership, routing intents, governed-doc inventory, and lint rules live in `.docpact/config.yaml`
- minimum proof and upstream-resolution notes live in `docs/agents/repo-validation.md`
- stable path groups, upstream handoffs, and release topology live in `docs/agents/repo-architecture.md`
- repo-local documentation maintenance is enforced locally by the pre-push docpact gate; `.github/workflows/ai-doc-lint.yml` is manual-dispatch fallback
- the main routing intents are `typescript-sdk`, `validation-contract`, `python-sdk`, `generation-and-release`, `upstream-refresh`, `release-setup`, `proof`, `repo-docs`, and `root-integration`
- TypeScript validation normalization is owned by `sdks/typescript/src/core/config/ValidationConfig.ts`, while schema-level custom issue codes for generated localized-text checks are injected from `sdks/typescript/scripts/generate-zod-schemas.ts` into committed schema output under `sdks/typescript/src/schemas/**`

## Minimal Execution Facts

Keep these entry-level facts in `AGENTS.md`. Use `README.md`, `docs/agents/repo-validation.md`, and the release / automation docs for fuller detail.

- root Node.js runtime: exact `24.19.0` in `.nvmrc`, package engines, and TypeScript CI jobs
- root package manager: `pnpm@11.24.0`
- root workspace and lockfile: `pnpm-workspace.yaml` and `pnpm-lock.yaml`
- routine branch base: `main`
- routine PR base: `main`
- published packages:
  - `@tiangong-lca/tidas-sdk` from `sdks/typescript/`
  - `tidas-sdk` from `sdks/python/`
- canonical verification baseline:
  - `./scripts/ci/verify-typescript-package.sh`
  - `./scripts/ci/verify-python-package.sh`
- the local pre-push hook runs docpact and then both verification scripts for source, tag and unrecognized pushes; only complete valid branch-deletion-only input skips those source gates
- `.github/workflows/ci.yml` runs both canonical verifiers for main-target dependency/configuration/workflow PRs at their exact heads and remains manually dispatchable; tag and publish workflows run release-time package verification
- dependency monitoring scope, cadence and review boundaries live in `docs/agents/dependency-updates.md`; configuration-only maintenance has a dedicated narrow Docpact rule, while existing manifest, lock and source review requirements remain active
- upstream refresh helpers:
  - `./scripts/ci/generate-typescript-sdk.sh`
  - `./scripts/ci/generate-python-sdk.sh`
- the default upstream generation pin is the exact `tidas-tools` commit declared by `TIDAS_TOOLS_SHA`; moving branch tips are not valid generation inputs
- the public specification pin is the exact archive and manifest identity declared by `scripts/ci/tidas-spec-pin.json`; generation and verification must use the same verified archive for schemas, the schema lock, and the public methodologies. A reviewed candidate may additionally pin its repository-authored public paths; a formal release derives those paths from the hash-verified manifest.
- a formal spec event advances the package-input pin and the separate public-rule source pin from that same hash-verified archive before TypeScript verification; unchanged rule bytes still receive the new exact source identity, while a changed digest is copied only from the verified archive.
- `.github/workflows/sync-from-tidas-tools.yml` accepts both `tidas_tools_changed` and `tidas_spec_released`. A spec event must carry the canonical package/version/source/archive/manifest identity and stable `event_key`; package and bump choices are grouped in `release_options` within GitHub's dispatch limit. Exact replays are no-ops. A reviewed non-release candidate may become the same-version formal release only when its archive and manifest digests are identical and its candidate provenance is explicit; the exact historical 0.2.0 promotion remains a narrow exception because its packaged README changed. Every other stale or same-version conflict fails closed. The workflow updates the spec pin only from that event and never treats a branch tip as a release input.
- release tags:
  - `typescript-v<version>`
  - `python-v<version>`

## Ownership Boundaries

The authoritative path-level ownership map lives in `.docpact/config.yaml`.

At a human-readable level, this repo owns:

- `sdks/typescript/**` for the TypeScript package source, examples, runtime assets, and package-local release docs
- `sdks/typescript/src/core/config/ValidationConfig.ts` for the normalized validation issue contract returned by `validateEnhanced()`
- `sdks/python/**` for the Python SDK source, tests, schemas, and package-local release docs
- `package.json`, `scripts/ci/**`, and `.github/workflows/{ci,publish,sync-from-tidas-tools,tag-release-from-merge}.yml` for generation, verification, tagging, and publish automation
- `README.md`, `docs/agents/**`, `docs/release-setup.md`, `docs/upstream-automation.md`, `.docpact/**`, and `.github/workflows/ai-doc-lint.yml` for repo-local governance and retained docs

This repo does not own:

- standalone conversion, export, or methodology tooling behavior
- public spec/docs-site wording
- workspace integration state after merge

Route those tasks to:

- `tidas-tools` for execution-oriented generation helpers, product profiles, runtime rulesets, taxonomies, optional methodologies, and standalone tooling behavior
- `tidas-spec` for the versioned public specification source and release archive; the SDK owns only its exact pin and consumption boundary
- `tidas` for public docs-site wording and presentation content
- `lca-workspace` for root integration after merge

## Branch And Delivery Facts

- GitHub default branch: `main`
- true daily trunk: `main`
- routine branch base: `main`
- routine PR base: `main`
- branch model: `M1`

`tidas-sdk` does not use a separate promote line. Normal implementation merges to `main`, and later workspace delivery still requires a root submodule bump when the updated SDK snapshot should ship through `lca-workspace`.

## Operational Invariants

- do not treat `tidas` as the immediate code-generation upstream when package refresh behavior actually depends on `tidas-tools`
- TypeScript runtime assets are selected and integrity-checked through the upstream Rust `assets/asset-lock.v1.json`; the committed package copy includes that authoritative lock
- TypeScript generation and verification must install the complete workspace dependency graph from the root `pnpm-lock.yaml` through the shared `pnpm install --frozen-lockfile` helper; package-local lockfiles and npm fallback installs are not valid
- keep pnpm 11's default minimum-release-age protection; any latest-stable exception in `pnpm-workspace.yaml` must name an exact reviewed package version and must not use an unversioned package or wildcard
- GitHub TypeScript jobs use the pinned `pnpm/setup` successor action for pnpm 11.24.0 and Node 24.19.0; `pnpm/action-setup` is a pnpm 10-or-older path and must not be restored
- the TypeScript SDK has one compiler track: standard `typescript@7.x`; legacy compiler consumers, aliases, `ts-node`, `ts-jest`, and TypeScript-ESLint are not valid fallbacks
- Zod schemas are rendered directly from the locked upstream JSON Schema assets; generation must not parse generated TypeScript or invoke a package runner, and unsupported schema shapes must fail instead of emitting permissive fallback validators
- the `0.2.x` validation boundary consumes every active locked Draft-07 keyword, uses exact-pointer allowlists for domain overlays, and fails generation on an unknown keyword, format, or overlay location
- Oxlint owns JavaScript/TypeScript lint, including type-aware deprecation checks; Node 24.19.0's test runner owns package tests, while `tsc` remains the independent release typecheck
- release proof must load every built tarball export through CJS, ESM, and TS7 declarations, execute the maintained examples, and enforce the recorded line/branch/function coverage ratchets
- generated localized-text checks in the TypeScript schemas must keep emitting stable custom validation codes so downstream UIs can map them without parsing prose
- generated Flow validators must preserve the upstream type-aware name condition: Elementary flows may omit synthetic qualifiers, while Product, Waste, and Other flows require both qualifier fields
- public schemas and the two public methodology files refresh from the pinned immutable `tidas-spec` archive; the W9 public-rule API has its own exact index/schema/source pin, now reviewed against the same 0.2.2 candidate source. Product profiles, remaining mixed runtime rulesets, taxonomies, and optional methodologies continue to come from the exact `tidas-tools` commit until their separate W11 disposition
- the public-rule SDK result may contain stable public IDs, locations, applicability, normative level, sources, and cases, but never severity, phase, blocker defaults, waivers, product profiles, or action authorization
- generated build output under `sdks/typescript/dist/**`, `sdks/python/dist/**`, and `sdks/python/htmlcov/**` is useful for packaging checks but is not the first durable edit surface
- merged repo PRs here are repo-complete, not workspace-delivery complete

## Documentation Update Rules

- if a machine-readable repo fact, routing intent, or governed-doc rule changes, update `.docpact/config.yaml`
- if a human-readable repo contract, branch rule, or hard boundary changes, update `AGENTS.md`
- if proof expectations or upstream-resolution notes change, update `docs/agents/repo-validation.md`
- if repo shape, stable path groups, or upstream handoff explanations change, update `docs/agents/repo-architecture.md`
- if registry setup or trusted-publishing prerequisites change, update `docs/release-setup.md`
- if cross-repo sync design or automation responsibilities change, update `docs/upstream-automation.md`
- if landing context or basic setup commands change, update `README.md`
- do not copy the same rule into multiple docs just to make it easier to find

## Hard Boundaries

- do not treat `tidas` as the immediate generation upstream for current SDK refreshes
- do not copy public specification assets from an unpinned `tidas-tools` checkout or from generated package output; use the verified archive resolved by `scripts/ci/lib/tidas-spec-source.sh`
- do not move standalone conversion or export logic into the SDK packages
- do not treat generated output as the only durable source of truth when generation behavior changes
- do not treat a merged repo PR here as workspace-delivery complete if the root repo still needs a submodule bump

## Workspace Integration

A merged PR in `tidas-sdk` is repo-complete, not delivery-complete.

If the change must ship through the workspace:

1. merge the child PR into `tidas-sdk`
2. update the `lca-workspace` submodule pointer deliberately
3. complete any later workspace-level validation that depends on the updated SDK snapshot

## Local Docpact Push Gate

Install the versioned local hook once per checkout:

```bash
./scripts/install-git-hooks.sh
```

Except for validated branch-deletion-only pushes, the `pre-push` hook runs `scripts/docpact-gate.sh`, which delegates CLI lookup to `scripts/docpact` and performs strict config validation plus enforced lint before the push leaves the machine. It then runs both package verification scripts as the local test gate. The wrapper checks `DOCPACT_BIN`, Cargo install locations, Homebrew install locations, and then `PATH`, so local agent shells should not fail only because bare `docpact` is unavailable. The default comparison base is `origin/main`. Override it for unusual stacks with `DOCPACT_BASE_REF=<ref>` or `scripts/docpact-gate.sh --base <ref>`. The gate writes its detailed report to a temporary file so normal pushes do not create `.docpact/runs/` artifacts.
