---
title: tidas-sdk Release Setup
docType: guide
scope: repo
status: active
authoritative: false
owner: tidas-sdk
language: en
whenToUse:
  - when a task changes release environments, trusted publishing, registry prerequisites, or tag-to-publish workflow behavior
  - when reviewing the release-setup governed doc referenced by docpact routing
whenToUpdate:
  - when publish workflow identity, environment names, secret names, or trusted-publishing prerequisites change
checkPaths:
  - docs/release-setup.md
  - .github/workflows/publish.yml
  - .github/workflows/tag-release-from-merge.yml
  - .nvmrc
  - package.json
  - .docpact/config.yaml
lastReviewedAt: 2026-10-18
lastReviewedCommit: 3c0b7eb4fab554418f7e71620146e65366a9d246
lastReviewedNote: "Reviewed SDK #168 after composing delivered #169: exact Actions pins and real Python artifact transfer retain the public Model/Process tests and 95/75/70 coverage gates; package graph, versions, runtime/source identities and release authority are unchanged."
related:
  - ../AGENTS.md
  - ../.docpact/config.yaml
  - ./upstream-automation.md
  - ./agents/repo-validation.md
---

# Release Setup

This document captures the one-time repository and registry configuration required for the `tidas-sdk` release workflows.

## Cross-Repository Automation

If you want `tiangong-lca/tidas-spec` releases or `tiangong-lca/tidas-toolkit` changes to automatically rebuild and release the SDK packages in this repository, use the architecture described in [upstream-automation.md](./upstream-automation.md).

Recommended model:

- `tidas-spec` publishes the reviewed public archive through `tidas_spec_released`, and `tidas-tools` detects execution-oriented SDK changes through `tidas_tools_changed`
- `tidas-tools` dispatches into `tiangong-lca/tidas-sdks`
- `tidas-sdk` verifies the exact `tidas-spec` archive and `tidas-tools` SHA, then opens a release-prep PR
- after merge, `tidas-sdk` creates package tags
- the existing `publish.yml` workflow publishes from those tags

Current workflow files:

- `.github/workflows/sync-from-tidas-tools.yml`
- `.github/workflows/tag-release-from-merge.yml`
- `.github/workflows/publish.yml`

Important constraint:

- if tag creation is automated, do not rely on the default workflow `GITHUB_TOKEN` for those tag pushes
- use a GitHub App token or fine-grained PAT so the downstream tag-triggered publish workflow can run as expected
- tag creation runs the relevant package verification script before creating a package tag

Operational preference:

- keep registry ownership and Trusted Publishing configuration in `tiangong-lca/tidas-sdks`
- keep `publish.yml` as the formal package release entrypoint
- automate PR creation and tag creation, not cross-repository direct publishing
- `.github/workflows/ci.yml` validates main-target dependency/configuration/workflow PRs through both existing verifiers and remains manually dispatchable; ordinary source pushes retain the local pre-push gate
- if a release-prep PR changes the machine-readable TypeScript validation contract, call that out explicitly so downstream consumers can review any UI or API mapping impact before tagging
- before tagging a spec-driven SDK release, confirm the generated package-input pin and bundled W9 public-rule source identity both name the same released spec commit; compatibility-only runtime ruleset summaries remain separately governed
- a reviewed candidate spec archive may be used for qualification without changing package versions or tags; only the canonical `tidas_spec_released` event may replace it with formal release identity and enter normal release preparation, and a same-version promotion requires identical archive and manifest digests unless it is the exact retained 0.2.0 exception

Required secrets:

- in `tiangong-lca/tidas-sdks`: `TIDAS_RELEASE_AUTOMATION_TOKEN`
- in `tiangong-lca/tidas-toolkit`: `TIDAS_SDK_AUTOMATION_TOKEN`

The current workflows expect a token that can:

- read `tiangong-lca/tidas-toolkit`
- push automation branches to `tiangong-lca/tidas-sdks`
- open PRs in `tiangong-lca/tidas-sdks`
- create tag refs in `tiangong-lca/tidas-sdks`
- create a repository dispatch event from `tiangong-lca/tidas-toolkit` into `tiangong-lca/tidas-sdks`

If you prefer a GitHub App instead of a PAT, keep the same secret names but update the workflows to mint an installation token at runtime.

## GitHub Repository

Create this protected environment in `tiangong-lca/tidas-sdks`:

- `pypi-release`

Recommended settings:

- required reviewers enabled
- prevent self-review enabled
- only maintainers who can approve package releases listed as reviewers

`npm-release` is optional. The current TypeScript publish job uses npm Trusted Publishing without a GitHub deployment environment. Only create `npm-release` if you later decide to gate npm publishes with a GitHub environment, and update the npm Trusted Publisher configuration to match.

The publish workflow file is fixed at:

- `.github/workflows/publish.yml`

Do not rename that workflow file without updating the registry-side trusted publisher configuration.

## npm Trusted Publisher

Configure Trusted Publishing for `@tiangong-lca/tidas-sdk` on npm with:

- organization or user: `tiangong-lca`
- repository: `tidas-sdks`
- workflow filename: `publish.yml`

The TypeScript publish job expects tags named `typescript-vX.Y.Z`.

Leave the environment name unset unless the workflow is explicitly updated to use a GitHub environment for npm releases.

## PyPI Trusted Publisher

Configure a Trusted Publisher for project `tidas-sdk` on PyPI with:

- owner: `tiangong-lca`
- repository name: `tidas-sdks`
- workflow filename: `publish.yml`
- environment name: `pypi-release`

The Python publish job expects tags named `python-vX.Y.Z`.

If the PyPI project does not exist yet, register a pending publisher first so the first trusted publish can create it.

## Repository Settings

- GitHub Actions must be enabled for the repository.
- GitHub-hosted runners must be used for trusted publishing.
- Maintainers should avoid long-lived `NPM_TOKEN` / `PYPI_API_TOKEN` secrets once Trusted Publishing is configured.

## Operational Notes

- the TypeScript publish job activates the exact `pnpm@11.24.0` declared at the
  repository root and verifies the frozen `pnpm-lock.yaml` before publication.
- pnpm 11.24.0 and Node 24.19.0 are installed through the SHA-pinned `pnpm/setup` successor
  action; the legacy `pnpm/action-setup` path is not compatible with this track.
- the TypeScript package pins its public publish target to
  `https://registry.npmjs.org/`; do not rely on runner-level registry defaults.
- `publish.yml` validates that the Git tag matches the package version before upload.
- Python distributions retain the archived `python-dist` / `dist/*` transfer;
  downloads fail on artifact digest mismatch. PR CI qualifies the same action
  pair with real distributions and a separate producer inventory, without
  entering the protected release environment or acquiring publication authority.
- setup-uv uses its event-sensitive `auto` cache policy with pruning disabled;
  tag/release cache restrictions do not waive package verification.
- post-merge tag detection treats an absent `typescript-vX.Y.Z` or `python-vX.Y.Z`
  tag for the current package version as a pending release; an existing matching
  tag prevents unrelated later pushes from attempting the same release again.
- npm and PyPI releases are independent; configure both publishers even if only one package is released initially.
- Issue #144's TypeScript-only `0.3.0` release intentionally breaks the pre-1.0
  mixed-ruleset compatibility API. Publish and verify this tag independently of
  Python; downstream CLI must explicitly adopt the new SDK line before its own
  compatible release. The prior complete published combination remains rollback.
- if a repository or package rename ever happens, update both the workflow and the trusted publisher registration before the next release.
