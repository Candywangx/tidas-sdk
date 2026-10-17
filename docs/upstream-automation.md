---
title: tidas-sdk Upstream Automation Design
docType: guide
scope: repo
status: active
authoritative: false
owner: tidas-sdk
language: en
whenToUse:
  - when a task changes cross-repo automation between tidas-spec, tidas-tools, and tidas-sdk
  - when reviewing how upstream generation and release-prep PRs should work
whenToUpdate:
  - when upstream trigger shape, dispatch payload, sync workflow layout, or automation authentication changes
checkPaths:
  - docs/upstream-automation.md
  - scripts/ci/**
  - .github/workflows/sync-from-tidas-tools.yml
  - .github/workflows/tag-release-from-merge.yml
  - .nvmrc
  - package.json
  - .docpact/config.yaml
lastReviewedAt: 2026-10-18
lastReviewedCommit: 547267760a80085ebddea118059fc686e94bd28d
lastReviewedNote: "Reviewed SDK #168 after composing delivered #169: exact Actions pins and real Python artifact transfer retain the public Model/Process tests and 95/75/70 coverage gates; package graph, versions, runtime/source identities and release authority are unchanged."
related:
  - ../AGENTS.md
  - ../.docpact/config.yaml
  - ./release-setup.md
  - ./agents/repo-architecture.md
---

# Upstream Automation Design

This document describes the recommended cross-repository automation path for keeping `tidas-sdk` in sync with the versioned public archive from `tiangong-lca/tidas-spec` and execution-oriented changes from `tiangong-lca/tidas-toolkit`.

The checked-in workflows implement this flow. Repository secrets and external registry bindings still require live verification; their existence is not proved by this document. Publication remains owned by the existing tag-driven SDK workflow.

W9 public-rule development uses `scripts/ci/tidas-public-rules-pin.json` and `sdks/typescript/scripts/sync-public-rules.ts` as a separately verified index/schema contract. W10S first qualified the optional Process/LCIA Method review-report reference against an exact 0.2.0 candidate archive. The package-input pin later advanced through verified `tidas_spec_released` events to formal releases. Issue #146 qualified the exact reviewed 0.2.2 candidate so Process review may be a singleton object or ordered non-empty array; Issue #148 promotes both the package-input and public-rule pins to the byte-identical formal 0.2.2 release before publishing TypeScript 0.3.1. Source commit, archive, and manifest hashes stay explicit, and the public-rule API pin follows the same qualified source so a single SDK package cannot combine mismatched specification identities. Product-owned execution profiles and the legacy mixed ruleset retain their separate W11 disposition.

Issue #156 adopts the 0.2.3 Process reference rules. The formal spec event
updates both pins from one verified archive before package verification. The
index and schema bytes may be unchanged while their source commit advances;
that exact identity still belongs in the TypeScript package. The initial
0.2.3 auto-sync failed when only the package-input pin advanced and the
public-rule source remained at 0.2.2; this workflow now fails closed on archive
or bundled-byte drift and refreshes both together.

The goal is:

1. `tidas-spec` publishes a new reviewed public archive (`tidas_spec_released`), or `tidas-tools` changes in a way that affects generated SDK content (`tidas_tools_changed`).
2. `tidas-sdk` regenerates the Python and TypeScript SDKs from the exact spec archive and tools commit.
3. If generated output changes, `tidas-sdk` opens a release-prep PR.
4. After the PR is merged, `tidas-sdk` creates package tags.
5. Existing tag-driven release automation publishes the packages.

## Design Principles

- `tidas-sdk` remains the package-owning repository.
- `tidas-spec` owns the public specification source and release archive; `tidas-sdk` records and verifies only the exact archive pin.
- npm and PyPI publishing stay in `tidas-sdk/.github/workflows/publish.yml`.
- `tidas-tools` should trigger sync, not publish packages directly.
- auto-generated code changes should still land through a normal PR for review and local/release verification.
- TypeScript and Python package versions stay independent.

## Recommended Flow

```text
tidas-spec release or tidas-tools push/merge
  -> detect SDK-relevant upstream change
  -> repository_dispatch to tiangong-lca/tidas-sdks
  -> tidas-sdk sync workflow regenerates SDKs from exact tidas-spec archive + tidas-tools SHA
  -> if no diff: stop
  -> if diff: bump package versions, commit bot branch, open PR
  -> merge PR
  -> tidas-sdk post-merge workflow creates package tag(s)
  -> publish.yml runs from package tag(s)
  -> npm / PyPI release completes
```

## Why This Split

This design keeps ownership aligned:

- `tidas-spec` owns the public schemas, schema lock, and public methodologies.
- `tidas-tools` owns conversion logic, execution-oriented assets, and the upstream trigger for tool changes.
- `tidas-sdk` owns generated artifacts, package versions, PR review, tags, and publishing.

That avoids a fragile setup where one repository publishes another repository's packages or silently changes package metadata outside the owning repo.

## Workflow Layout

### 1. `tidas-tools`: upstream change detector

The workflow in `tiangong-lca/tidas-toolkit` runs on merges to `main` and filters for SDK-relevant paths.

Recommended responsibilities:

- decide whether the merged change should trigger SDK regeneration
- determine which package families are affected:
  - `typescript`
  - `python`
  - `both`
- determine the default version bump:
  - `patch`
  - `minor`
  - `major`
- send a `repository_dispatch` event to `tiangong-lca/tidas-sdks`

The specification release payload is strict and content-addressed:

```json
{
  "event_type": "tidas_spec_released",
  "client_payload": {
    "event_key": "@tiangong-lca/tidas-spec@0.2.0:<archive-sha256>:<manifest-sha256>",
    "package": "@tiangong-lca/tidas-spec",
    "version": "0.2.0",
    "source_commit": "<40-char tidas-spec SHA>",
    "archive_file": "tiangong-lca-tidas-spec-0.2.0.tgz",
    "archive_url": "https://github.com/tiangong-lca/tidas-spec/releases/download/v0.2.0/tiangong-lca-tidas-spec-0.2.0.tgz",
    "archive_sha256": "<64-char SHA256>",
    "manifest_sha256": "<64-char SHA256>",
    "release_options": {
      "packages": ["typescript", "python"],
      "typescript_bump": "minor",
      "python_bump": "minor"
    },
    "reason": "reviewed public specification release"
  }
}
```

The eight release-identity fields plus `release_options` and optional `reason`
stay within GitHub's ten-top-level-property limit. The receiver also accepts
the older separate `packages` and bump fields during transition. A same-version
candidate promotion is accepted only when the current pin is explicitly marked
as a non-release candidate and its archive and manifest digests exactly match
the canonical formal release event. The pre-publication 0.2.0 candidate at
commit `58dc72f5` remains one exact historical exception: it had the same schema
asset digests as formal release `f71ed300`, but its archive and manifest differ
because the packaged README changed. Every other same-version identity conflict
remains an error.

The existing tools dispatch payload remains:

```json
{
  "event_type": "tidas_tools_changed",
  "client_payload": {
    "tidas_tools_sha": "<merged commit sha>",
    "packages": ["typescript", "python"],
    "typescript_bump": "patch",
    "python_bump": "patch",
    "reason": "schema update"
  }
}
```

Use `repository_dispatch` instead of `workflow_dispatch` so the sender does not need Actions write permission on the target repository.
`tidas_tools_sha` is mandatory and must be a full 40-character commit; the sync
workflow rejects an empty value or branch/ref fallback.

### 2. `tidas-sdk`: sync and release-prep PR

The workflow in `tiangong-lca/tidas-sdks` runs on:

- `repository_dispatch` with type `tidas_tools_changed` or `tidas_spec_released`
- optional manual `workflow_dispatch` for recovery or re-run

Current implementation file:

- `.github/workflows/sync-from-tidas-tools.yml`

Recommended responsibilities:

1. check out `tidas-sdk`
2. check out `tiangong-lca/tidas-toolkit` at the exact tools SHA (the spec event derives this from the current tools pin)
3. verify that checkout against its Rust `assets/asset-lock.v1.json`
4. resolve and verify the exact `tidas-spec` archive declared by `scripts/ci/tidas-spec-pin.json`
5. install the TypeScript workspace dependency graph with exact Node `24.19.0`
   and `pnpm@11.24.0` from the root `pnpm-lock.yaml` through
   `pnpm install --frozen-lockfile`
6. regenerate SDKs with:
   - `TIDAS_TOOLS_SOURCE_MODE=auto`
   - `TIDAS_TOOLS_PATH=<checked out tools path>`
   - `TIDAS_TOOLS_SHA=<checked out exact commit>`
7. run local parity checks:
   - `./scripts/ci/verify-typescript-package.sh`
   - `./scripts/ci/verify-python-package.sh`
8. for `tidas_spec_released`, validate the event, download and hash-check the notified archive, and refresh the exact package-input and public-rule pins/bytes from it before TypeScript verification; an exact replay is a no-op, an explicit byte-identical candidate may promote to formal release, and every other stale or same-version conflicting identity fails closed
9. detect whether TypeScript and/or Python outputs changed, including a changed spec pin
10. bump only the affected package version(s) to the next unpublished version in the target registry
    - TypeScript regeneration intentionally leaves reviewed package output uncommitted before version preparation. The filtered `pnpm version` command uses `--no-git-checks` solely for that dirty-tree precondition; it still makes no tag or commit, and the later package verification and PR review remain mandatory.
11. update the repository's exact tools commit only for a tools event; update the spec archive pin only from a spec event
12. record deterministic review metadata in every Docpact-required governed document
13. commit generated package files, exact pins, and governed review records to a bot branch
14. open or update a release-prep PR against `main`

Validation-contract safeguard for TypeScript refreshes:

- require the frozen pnpm 11.24.0 workspace install on Node 24.19.0 and toolchain contracts to prove every resolved TypeScript compiler is 7.x and the packed SDK carries no compiler or generator tooling
- render Zod modules directly from the asset-lock-selected JSON Schema directory; do not restore an intermediate TypeScript parser or permissive fallback generator
- when regeneration touches localized-text schemas or validation helpers, keep the post-processing that injects `params.validationCode` into custom localized-text issues
- when Flow schemas contain cross-field `if` / `then` conditions, keep the generated Zod/Pydantic type-aware validator post-processing
- confirm the committed TypeScript package still normalizes raw Zod issues into stable `validationIssues` codes for downstream consumers
- for generator implementation changes, compare the candidate against a pre-change baseline with `pnpm --filter @tiangong-lca/tidas-sdk verify:schema-generation-parity` before replacing the baseline build
- do not default a generator semantics change to a patch: record the compatibility decision and choose a version that prevents existing consumers from receiving stricter validation implicitly (`0.2.0` for issue #101)
- run the maintained examples and built-tarball CJS/ESM/declaration consumer contract before a release-prep PR is reviewable
- call this out in the release-prep PR when the machine-readable validation contract changes

Recommended branch name:

- `automation/tidas-tools-sync-<short-sha>`

Recommended PR body content:

- upstream `tidas-tools` commit SHA
- `tidas-spec` archive version, source commit, and archive/manifest SHA-256
- affected packages
- version bump choice
- generation summary
- verification commands used

### 3. `tidas-sdk`: post-merge auto-tagging

The workflow in `tiangong-lca/tidas-sdks` runs after the automation PR merges to `main`.

Current implementation file:

- `.github/workflows/tag-release-from-merge.yml`

Recommended responsibilities:

1. inspect the merged commit
2. detect which package version(s) changed compared with the previous `main`
   commit, or whose current version still lacks its expected package tag
3. fail early if a target package version already exists in npm or PyPI
4. create release tag(s):
   - `typescript-vX.Y.Z`
   - `python-vX.Y.Z`
5. push those tags

Important constraint:

If the repository still relies on tag pushes to trigger `publish.yml`, the tag push must be created with a GitHub App token or PAT. A tag created with the default workflow `GITHUB_TOKEN` may not trigger the downstream publish workflow as intended.

### 4. `tidas-sdk`: existing publish workflow

No architectural change is required for:

- `.github/workflows/publish.yml`

That workflow should remain the package publishing entrypoint because npm and PyPI Trusted Publishing both bind to the concrete repository workflow identity.

## Required GitHub Configuration

### Authentication

Use one shared GitHub App installed on both repositories, or a tightly scoped fine-grained PAT if an App is not available yet.

GitHub App is preferred because it is easier to audit and rotate.

Recommended permissions:

- `Contents: Read and write`
- `Pull requests: Read and write`
- `Metadata: Read`

If you choose `workflow_dispatch` instead of `repository_dispatch`, also grant:

- `Actions: Read and write`

### Secrets

In `tidas-tools`:

- `TIDAS_SDK_AUTOMATION_TOKEN`
  - fine-grained PAT today, or a future GitHub App installation token minted at runtime
  - must be able to dispatch into `tiangong-lca/tidas-sdks`

In `tidas-sdk`:

- `TIDAS_RELEASE_AUTOMATION_TOKEN`
  - fine-grained PAT today, or a future GitHub App installation token minted at runtime
  - must be able to push automation branches, open PRs, and create release tags

If the same GitHub App is used in both repositories, the workflows can mint installation tokens at runtime instead of storing long-lived PATs.

### Environments and registries

Keep the existing protected release environment:

- `pypi-release`

`npm-release` is optional and should only be added if TypeScript publishes are later gated behind a GitHub environment. If that happens, update the npm Trusted Publisher configuration to use the same environment name.

Keep Trusted Publishing bound to:

- repository: `tiangong-lca/tidas-sdks`
- workflow: `.github/workflows/publish.yml`

If fully unattended publishing is desired, update environment protection rules and trusted publisher expectations deliberately. Otherwise keep release approvals in place and automate only up to tag creation.

## Version Bump Policy

Recommended default policy:

- schema-compatible additive change: `minor`
- generator-only fix with no API break: `patch`
- breaking schema or generated API change: `major` after 1.0; while pre-1.0,
  a reviewed `minor` release may deliberately establish a new incompatible
  `^0.x` line (Issue #144 retires the mixed-ruleset TypeScript API in `0.3.0`)

Implementation options:

- simple mode: `tidas-tools` dispatch payload explicitly includes bump levels
- managed mode: `tidas-tools` labels PRs and the workflow maps labels to bump levels
- conservative mode: default to `patch` and let reviewers adjust the release-prep PR before merge

For the first implementation, conservative mode is the safest.

## Change Detection Rules

Recommended behavior inside the `tidas-sdk` sync workflow:

- if no generated output changes, do not open a PR
- if only TypeScript files changed, bump and release only TypeScript
- if only Python files changed, bump and release only Python
- if both changed, prepare both releases in one PR but create independent tags after merge

Do not force both packages to release together when only one generated surface changed.

## Failure Handling

Recommended safeguards:

- if generation fails, fail the workflow and leave logs in the workflow run
- if verification fails, fail before opening a PR
- if a matching automation PR already exists for the same upstream SHA, update it instead of opening duplicates
- if release tags already exist, fail fast instead of force-pushing or retagging
- if a package version merged but its tag gate failed, merge the corrective
  governance/automation change normally; tag-absence detection will retry that
  still-unpublished version without requiring a version bump
- if publishing fails after tag creation, recover through the normal tag-based release process instead of rewriting history

The migrated sync receiver clones the public canonical upstream without embedding the automation token in argv or the stored remote URL. Local verification keeps the selected Git account context while isolating repository-local Git bindings; exact upstream commit and asset-lock validation remain mandatory.
