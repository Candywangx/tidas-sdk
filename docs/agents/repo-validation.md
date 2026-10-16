---
title: tidas-sdk Validation Guide
docType: guide
scope: repo
status: active
authoritative: false
owner: tidas-sdk
language: en
whenToUse:
  - when a tidas-sdk change is ready for local validation
  - when deciding the minimum proof required for package, generation, automation, or docs changes
  - when writing PR validation notes for tidas-sdk work
whenToUpdate:
  - when the repo gains new canonical verify wrappers
  - when change categories require different proof
  - when release automation or upstream-resolution behavior changes
checkPaths:
  - docs/agents/repo-validation.md
  - .docpact/config.yaml
  - .nvmrc
  - scripts/ci/**
  - sdks/typescript/**
  - sdks/python/**
  - docs/release-setup.md
  - docs/upstream-automation.md
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
  - ./repo-architecture.md
  - ../release-setup.md
  - ../upstream-automation.md
---

## Default Baseline

Unless the change is doc-only, the canonical verification scripts are:

```bash
./scripts/ci/verify-typescript-package.sh
./scripts/ci/verify-python-package.sh
```

These scripts are the best repo-wide proof because they mirror CI expectations and current upstream-resolution behavior.

## Validation Matrix

| Change type | Minimum local proof | Additional proof when risk is higher | Notes |
| --- | --- | --- | --- |
| TypeScript package source, examples, or package scripts | `./scripts/ci/verify-typescript-package.sh` | run `pnpm --filter @tiangong-lca/tidas-sdk test:coverage` when testable behavior changes | This covers the frozen pnpm 11.24.0/TS7 install on Node 24.19.0, correctness/suspicious/deprecation lint, both TS7 typechecks, Node tests, maintained examples, generated artifacts, build, and packability. The tarball contract loads every root/subpath through CJS, ESM, and TS7 declarations with `types: []` and `skipLibCheck: false`, then proves the pnpm consumer inherits no compiler tooling. Coverage is explicitly scoped to first-party package source/generation helpers so package-manager runtime code cannot dilute it; ratchets are lines 95%, branches 75%, functions 70%. |
| Public-rule API or separate index pin | `pnpm --filter @tiangong-lca/tidas-sdk verify-public-rules` plus focused contract/source tests and `./scripts/ci/verify-typescript-package.sh` | regenerate with `TIDAS_PUBLIC_RULES_SOURCE_ROOT=<exact-checkout> pnpm --filter @tiangong-lca/tidas-sdk sync-public-rules` and record the exact commit/hashes | The index pin remains a separate asset contract but binds to the same qualified source as the package-input pin, including reviewed candidates. Verification must reject changed bytes and stale identity, prove Process/Flow coverage and explicit not-covered kinds, and confirm no product policy fields enter the public result. |
| JSON Schema to Zod generator or domain overlays | `./scripts/ci/verify-typescript-package.sh` | before replacing the baseline build, run `pnpm --filter @tiangong-lca/tidas-sdk verify:schema-generation-parity` and record the exact baseline/candidate source plus intentional differences | The active Draft-07 vocabulary, runtime helper semantics, taxonomy dependencies, review conditions, and exact overlay locations have focused cases. Unknown keywords/formats/locations fail generation. Use explicit baseline/candidate directories when the default artifacts are not appropriate. |
| Python package source, scripts, or tests | `./scripts/ci/verify-python-package.sh` | run one focused pytest or generation step when the change is isolated | Record if the Python package still depends on generated artifacts from a specific upstream commit. |
| shared generation helpers under `scripts/ci/**` | run both verify scripts | run the matching focused automation regression script and `generate-*.sh` path if the task explicitly changes refresh behavior | Generation changes can affect both packages even if only one output changed. |
| release setup, tag, or publish workflows | run both verify scripts and `python3 ./scripts/ci/test-automation-contracts.py` | inspect `.github/workflows/**` and record any tag or environment assumptions checked locally | Tag creation and registry publication are separate from local package verification. Release detection must distinguish an untagged pending version from an already-tagged version. |
| repo contract or governed-doc changes only | `scripts/docpact validate-config --root . --strict` and `scripts/docpact lint --root . --staged --mode enforce` | run one focused route check such as `scripts/docpact route --root . --intent repo-docs --format text` or `upstream-refresh` when the change touches release / automation docs | Refresh review evidence even when prose-only governed docs change. |

## Upstream Resolution Notes

Facts that matter:

- TypeScript and Python generation resolve `tidas-tools` in this order:
  1. `TIDAS_TOOLS_PATH`
  2. sibling `../tidas-toolkit`, then the pre-rename `../tidas-tools`
  3. temporary clone
- every source must be a Git checkout at the exact `TIDAS_TOOLS_SHA`; the default
  pin is immutable and advances in the same generated PR as the package assets;
  dispatch/manual automation must supply a full 40-character SHA
- TypeScript and Python generation resolve `tidas-spec` as one verified archive: either a formal release or an explicitly reviewed, content-addressed candidate. Set `TIDAS_SPEC_ARCHIVE_PATH` for an explicit archive, use the sibling `tidas-spec/release/` archive in `auto` mode, or let the helper download the exact `releaseArchiveUrl` from `scripts/ci/tidas-spec-pin.json`.
- `scripts/ci/tidas-spec-assets.mjs verify` validates the archive SHA-256, manifest SHA-256, complete package inventory, source evidence, and the reviewed 39-file public subset before extraction. The 0.2.0 candidate explicitly pins five repository-authored public paths and retains manifest/hash proof for the other 34 imports. `assembly-plan` overlays every public path from spec, compares unchanged overlaps byte-for-byte, and excludes explicitly authored paths from the tools-equality requirement. A `tidas_spec_released` event is first validated by `update-tidas-spec-pin.py`; exact replays and explicit byte-identical candidate promotions are accepted, while stale, malformed, partial, formally pinned, or byte-changing same-version events fail closed. The exact historical 0.2.0 promotion remains separately bounded.
- `update-tidas-public-rules-pin.py` checks the same pinned archive and manifest, verifies the rule index/schema digests and existing bundled bytes, then updates both the source pin and TypeScript assets. Its exact replay is a no-op; a stale bundle or altered archive fails before package verification. A spec-driven refresh must prove the package-input and public-rule identities agree, even when the public-rule bytes are unchanged.
- `scripts/ci/tidas-tools-assets.mjs` validates the Rust
  `assets/asset-lock.v1.json`, all catalog entry hashes/sizes, and the packaged
  TypeScript runtime copy before generation succeeds. The SDK copy has a
  deterministic derived lock that records the upstream lock SHA and excludes
  only the two former mixed `runtime_rulesets` files; verification fails if
  either retired file remains packaged
- clean TypeScript generation and verification both install dependencies through
  `scripts/ci/lib/typescript-dependencies.sh`, which requires the root
  `pnpm-lock.yaml`, exact `pnpm@11.24.0`, and exact Node `24.19.0` from `.nvmrc`,
  then runs `pnpm install --frozen-lockfile` from the repository root
- pnpm's default one-day release-age gate remains active; the toolchain contract
  permits only exact, versioned exceptions recorded after reviewing a required
  latest-stable release
- `sdks/typescript/tests/toolchain-contract.test.mjs` rejects TypeScript majors
  below 7, legacy Compiler API consumers, removed tsconfig options, missing
  coverage ratchets, unusable tarball exports, and consumers that inherit
  compiler tooling
- generator changes should build the baseline before editing, then run
  `pnpm --filter @tiangong-lca/tidas-sdk verify:schema-generation-parity`; its automatic candidate directory
  is always cleaned and can be replaced by explicit baseline/candidate paths
- if you intentionally validate against a local checkout or archive, record both
  its path and exact commit/archive SHA in the PR note

## Validation Contract Notes

- TypeScript callers should prefer `validateEnhanced()` and consume the returned `validationIssues` array instead of parsing raw Zod error prose when stable UI or API behavior matters.
- Normalized validation issues should preserve `code`, `path`, `severity`, optional `params`, `message`, and `rawCode`.
- Generated localized-text checks must keep attaching `params.validationCode` so the downstream normalized code resolves to stable values such as `localized_text_zh_must_include_chinese_character` and `localized_text_en_must_not_contain_chinese_character`.
- Generated TypeScript and Python Flow validators must prove that an Elementary
  flow accepts `baseName` without synthetic qualifiers and Product, Waste, and
  Other flows reject missing `treatmentStandardsRoutes` or
  `mixAndLocationTypes`.
- Process and LCIA review validators must require scope, details, and reviewer
  whenever `@type` is not `Not reviewed`; the complete-review-report reference
  is optional, but a supplied reference must still satisfy `GlobalReferenceType`.
  Taxonomy dependency tests must prove both valid and invalid locked classification cases.
- Process quantitative-reference validation follows the pinned public schema:
  `Reference flow(s)` requires a Flow ID; `Other parameter`, `Functional unit`,
  and `Production period` require language-tagged `functionalUnitOrOther` and
  need no Flow ID. An omitted `typeOfDataSet` remains allowed; a supplied value
  still uses the enum. TypeScript Zod, the Python-shipped JSON Schema, and the
  generated Python Pydantic reference model prove the conditional requirement.
- Validation changes that correct historical under-validation require an
  explicit compatibility/version decision. Issue #101 uses `0.2.0`, not a
  patch, so `^0.1.x` consumers opt in deliberately.
- Issue #144 removes the TypeScript SDK's public `getTidasRuntimeRuleset`
  compatibility API and the mixed-ruleset pack fields. This is a breaking
  change while the package is pre-1.0; `0.3.0` is an opt-in minor line that
  cannot satisfy existing `^0.2.x` consumers. Python's API and version are
  unchanged. A compatible CLI release must pin this new line explicitly.
- If a change touches `sdks/typescript/scripts/generate-zod-schemas.ts`, `sdks/typescript/src/core/config/ValidationConfig.ts`, or committed schema output under `sdks/typescript/src/schemas/**`, mention in the PR note whether the validation contract changed or remained backward compatible.

## Process allocation/reference semantic API proof

SDK #160 adds the additive TypeScript 0.5.1 API independently of structural validation. Public root-API tests exercise the byte-identical SDK/Toolkit `process-semantics.v1.json` fixture, exact Flow evidence, resolver bounds/failures, singleton/array paths, stable diagnostics, full vector projection, legacy interpretations and immutability. Run the canonical TypeScript verifier plus coverage; TypeScript tarball qualification is source-package proof. Actual `typescript-v0.5.1` publication and consumer adoption need their separate exact package/registry receipts. Python source/API/version are unchanged.

## Minimum PR Note Quality

A good PR note for this repo should say:

1. which verify scripts ran
2. whether generation used a local `tidas-tools` checkout or the default resolution path
3. whether tag or publish proof is deferred to GitHub Actions

## Local Docpact Push Gate

Install the versioned local hook once per checkout:

```bash
./scripts/install-git-hooks.sh
```

Except for validated branch-deletion-only pushes, the `pre-push` hook runs `scripts/docpact-gate.sh`, which delegates CLI lookup to `scripts/docpact` and performs strict config validation plus enforced lint before the push leaves the machine. It then runs `./scripts/ci/verify-typescript-package.sh` and `./scripts/ci/verify-python-package.sh` as the local test gate. The wrapper checks `DOCPACT_BIN`, Cargo install locations, Homebrew install locations, and then `PATH`, so local agent shells should not fail only because bare `docpact` is unavailable. The default comparison base is `origin/main`. Override it for unusual stacks with `DOCPACT_BASE_REF=<ref>` or `scripts/docpact-gate.sh --base <ref>`. The gate writes its detailed report to a temporary file so normal pushes do not create `.docpact/runs/` artifacts. GitHub `CI` runs both existing verification jobs for main-target dependency/configuration/workflow PRs at the exact head and remains manually dispatchable. Source-only and documentation-only feature PRs retain the local checks; see [the dependency guide](dependency-updates.md) for monitoring, cancellation and review boundaries.

Upstream Git subprocesses clear inherited repository directory/index bindings but preserve process-scoped account configuration (`GIT_CONFIG_COUNT` / `GIT_CONFIG_PARAMETERS`). The explicit candidate checkout overrides inherited `core.worktree` / `core.bare` settings. Public upstream clones use credential-free canonical HTTPS; automation credentials remain confined to SDK write operations. Wrong SHA or asset locks still fail, and the default pin is unchanged.

TypeScript verification defaults to a temporary clone and retains that exact verified checkout through generation, tests, build and packing. Nested generation uses `verified-path` mode to recheck the same SHA and asset lock without cloning again. The owning process cleans temporary sources on success and failure. Standalone builds retain their existing sibling/offline fallback; canonical verification never falls back to it. The automation regression suite exercises differing sibling contents, the default clone path, strict reuse and cleanup.

`python3 scripts/ci/test-automation-contracts.py` is a lightweight automation gate
that runs before package bootstrap, including in the manual CI workflow. It uses
Python, Git, Bash and the dependency-free Node asset resolver; it must not invoke
pnpm, tsx or installed package tooling. The source-consistency fixture blocks pnpm
and executes the real verification prelude, then checks the pinned content visible
to a child process and cleanup. The full TypeScript package gate separately owns
actual bundler, compiler, package tests and packing proof.

The complete TypeScript verifier invokes generation with the explicit
`--defer-advisory-typecheck` option. This omits only the generator's early,
warning-only typecheck: after source regeneration, drift verification and lint,
the canonical verifier still runs its mandatory package and tools-tsconfig
checks before tests, examples, build and packing. Standalone generation keeps
its advisory check by default. Neither the option nor a cache hit waives source
pin/asset-lock checks, generated-output drift checks or any strict release gate.

The pre-push hook skips source validation only for complete, well-formed wire
input that deletes existing branch refs exclusively. Tag deletions, mixed
updates, empty/manual input, malformed or unsupported records, and classifier
failure all retain ordered Docpact, TypeScript and Python gates. This is not an
environment-selected bypass. `sh scripts/ci/test-pre-push.sh` exercises the real
hook with isolated gate transports; the existing automation suite includes it.
Direct canonical verification and release-time package proof remain unchanged.


### ILCD compatibility release qualification

SDK #158 consumes formal spec `0.3.0` at `32e1ba38da7d5f4f6245c6c1927f83b326cd5404`. The package-input and public-rule pins must bind the same released archive and manifest. Both canonical package verifiers must pass with the existing exact tools pin before tag-driven TypeScript `0.5.0` and Python `0.3.0` publication. Generator tests cover annotation-only `$comment`, bounded `not: { required: [...] }` alias exclusion, and parenthesized enum-array TypeScript output. Generated-schema tests exercise repeated Process/Flow fields, named classifications, model scaling aliases, LCIA geography aliases and strict unit items. Platform must verify the actual released package outside its Jest SDK mapper.

Python object generation preserves `allOf` negated-required groups through normalization and emits model validators using explicit field presence. Regression cases require either scaling/geography alias alone to pass and both aliases together to fail, including Python field-name input. This closes the gap between shipped JSON Schema validation and direct Pydantic construction.
