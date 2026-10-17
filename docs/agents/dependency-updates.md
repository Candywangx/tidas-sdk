---
title: SDK Dependency Updates
docType: guide
scope: repo
status: active
authoritative: false
owner: tidas-sdk
language: en
whenToUse:
  - when reviewing dependency or GitHub Actions update pull requests
  - when changing Dependabot monitoring or dependency PR validation
whenToUpdate:
  - when dependency monitoring scope, cadence, grouping or validation changes
checkPaths:
  - .github/dependabot.yml
  - .github/workflows/ci.yml
  - docs/agents/dependency-updates.md
lastReviewedAt: 2026-10-18
lastReviewedCommit: 3c0b7eb4fab554418f7e71620146e65366a9d246
lastReviewedNote: "Reviewed SDK #168 after composing delivered #169: exact Actions pins and real Python artifact transfer retain the public Model/Process tests and 95/75/70 coverage gates; package graph, versions, runtime/source identities and release authority are unchanged."
related:
  - ../../AGENTS.md
  - ./repo-validation.md
  - ../release-setup.md
---

# Dependency Updates

Dependabot checks the root pnpm workspace on Wednesdays at 04:00, the Python
package at 04:20, and GitHub Actions at 04:40, all in Asia/Shanghai. Every entry
uses a seven-day cooldown. npm and pip each permit two open version-update PRs;
Actions permits one. Compatible minor and patch updates are grouped by runtime
or development role for TypeScript, and together for Python. Major package
updates remain individually visible. Actions updates share one group.

The root `pnpm-lock.yaml` remains the TypeScript SDK and examples dependency
authority. Python uses `pip` monitoring of `sdks/python/pyproject.toml` because
the existing `uv.lock` is ignored rather than published as a repository input;
the canonical Python verifier still uses `uv`. Monitoring does not advance
`tidas-tools` or `tidas-spec` source pins, generated SDK assets, runtime versions,
or package versions. Review those changes through their existing contracts.

PRs into `main` touching dependency manifests, the pnpm lock/workspace, `.nvmrc`,
Dependabot configuration or workflows run the existing TypeScript and Python
verification jobs against the exact PR head. This includes maintainer-authored
dependency changes. Source-only and documentation-only feature changes retain
the existing local pre-push checks; manual CI remains available. Superseded CI
runs for the same PR are cancelled. PR checks have read-only repository access
and receive no publication credentials. The Python lane also uploads its real
verified wheel and sdist for a dependent read-only artifact roundtrip. Producer
filename, size and SHA256 outputs independently bind the downloaded bytes; the
archive checks and short retention are described in the validation guide.

Before accepting an update, inspect its actual manifest and lockfile diff and
run both canonical verifiers documented in [the validation guide](repo-validation.md).
They retain exact upstream commit/archive verification, generated-output drift
checks, tests, examples, package builds and tarball checks. A toolchain-major,
source-pin, schema or runtime-contract failure requires an explicit compatibility
decision; do not weaken validation or rewrite generated assets merely to make a
dependency PR pass. The existing Docpact manifest, lock and source review rules
continue to apply.

Sibling checkouts or archives at another revision fail the source checks. In an
isolated worktree, set `TIDAS_TOOLS_SOURCE_MODE=clone` and
`TIDAS_SPEC_SOURCE_MODE=clone` when invoking either verifier to resolve the exact
pinned public inputs independently of those siblings. The commit, archive and
manifest checks still apply.

The configuration takes effect from `main`. The weekly schedule does not delay
security updates; inspect repository security settings and the first actual
Dependabot update run separately. A merged configuration and passing local tests
do not prove that GitHub has executed its first updater or refreshed a lockfile.
Automatic merging is not configured. Package publication continues through the
existing reviewed tag and trusted-publishing workflow.

References: [Dependabot options](https://docs.github.com/en/code-security/reference/supply-chain-security/dependabot-options-reference),
[version-update configuration](https://docs.github.com/en/code-security/how-tos/secure-your-supply-chain/secure-your-dependencies/configure-version-updates).
