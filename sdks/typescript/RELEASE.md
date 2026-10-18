# Release Guide for `@tiangong-lca/tidas-sdk`

This package is released through the repository-owned GitHub Actions flow in `.github/workflows/publish.yml`.

## Default Path

Use this sequence for normal releases:

1. Start from the latest `origin/main`.
2. Prepare a release PR that includes:
   - the TypeScript package version metadata bump
   - any generated source updates required by upstream schema changes
   - documentation updates that should ship with the release
3. Run repository validation:

```bash
./scripts/ci/verify-typescript-package.sh
```

4. Merge the PR.
5. Wait for the existing `tag-release-from-merge.yml` automation: on the exact
   main merge it verifies the changed TypeScript package and creates
   `typescript-v<version>` from `sdks/typescript/package.json` automatically.
   Do not create tags manually in the
   normal path; manual tagging remains only the documented recovery/backfill
   fallback for an already-merged main commit.

6. Confirm the publish workflow completes successfully.
7. Confirm the new version is visible on npm and installable.

If the repository later adds a protected GitHub environment for npm releases, approve that environment before the publish job runs.

## Versioning

- Use semantic versioning.
- The Git tag must match `sdks/typescript/package.json` exactly:
  - package version `0.1.30` -> tag `typescript-v0.1.30`
- TypeScript and Python releases are independent. Do not wait for a Python release just to publish TypeScript.

## Validation Details

`./scripts/ci/verify-typescript-package.sh` performs the same checks expected by CI:

- `pnpm install --frozen-lockfile` from the repository root, using the exact
  Node `24.19.0` from `.nvmrc` and `pnpm@11.24.0` declared in `package.json`
- regenerate TypeScript artifacts from `tidas-tools`
- fail if generated source changes are not committed
- `pnpm --filter @tiangong-lca/tidas-sdk lint`
- `pnpm --filter @tiangong-lca/tidas-sdk typecheck`
- `pnpm --filter @tiangong-lca/tidas-sdk test`
- `pnpm --filter @tiangong-lca/tidas-sdk check:examples`
- `pnpm --filter @tiangong-lca/tidas-sdk build`
- `pnpm --filter @tiangong-lca/tidas-sdk pack --dry-run`

The package-local test suite also proves that the complete frozen dependency
tree contains only TypeScript 7 and that installing the tarball in a clean
consumer does not install TypeScript or generator tooling.

When the JSON Schema to Zod generator changes, build the pre-change baseline
first and run:

```bash
pnpm --filter @tiangong-lca/tidas-sdk verify:schema-generation-parity
```

The default baseline is `dist/schemas`. Use `TIDAS_ZOD_BASELINE_DIR` and
`TIDAS_ZOD_CANDIDATE_DIR` for explicit artifacts, and record the exact upstream
schema source in the PR validation note.

## `0.6.0` validation migration

SDK #171 prepares TypeScript 0.6.0 with exact Zod 4.6.7. Native bounds count
Unicode code points and RFC 3339 date-time requires seconds; normalized string
actualLength uses the same metric. The package README records examples and the
published 0.5.1 `^4.4.3` transitive-range limitation. Python stays 0.3.0 and the
public schemas, upstream pins and generated source expressions are unchanged.

Qualify a frozen 4.4.3 baseline and the complete candidate verifier, generation
parity, new actual-entity/scalar/combined diagnostics tests, coverage, examples
and packed CJS/ESM/TypeScript consumers. Keep the existing 95/75/70 ratchets.
A reviewed source/tarball candidate is not a registry receipt. Before merging
this version change to main, resolve authorization for the concrete existing
release chain: main push creates `typescript-v0.6.0` after verification using
the automation token, and that tag triggers npm publishing. Do not dispatch,
create a test tag, or bypass release gates to qualify this candidate.

## `0.2.0` compatibility boundary

Issue #101 deliberately prepares `0.2.0`, rather than a `0.1.x` patch. The
direct renderer corrects historical Zod under-validation for active Draft-07
semantics, including exact oneOf, review conditionals, taxonomy dependencies,
integer values, deep uniqueness, tuple additional-items behavior, formats, and
additional-properties policy. Existing `^0.1.x` consumers therefore do not
receive stricter validation automatically.

Before upgrading a consumer, run its real data cases and fix data that violates
the locked schema. Stable named CAS, localized-text, `common:other`, Required
MultiLang, and Flow issue code/path behavior remains covered by parity tests.

The coverage gate records the current ratchets:

- lines: 95%
- branches: 75%
- functions: 70%

If generation needs a specific local checkout of `tidas-tools`, provide it explicitly:

```bash
TIDAS_TOOLS_SOURCE_MODE=auto TIDAS_TOOLS_PATH=../tidas-toolkit ./scripts/ci/verify-typescript-package.sh
```

## Preparing the Version Bump

If you want a local helper for version editing without publishing, use:

```bash
pnpm release:prepare:patch:typescript
pnpm release:prepare:minor:typescript
pnpm release:prepare:major:typescript
```

These commands only update local version metadata files. They do not publish, create a git tag, or push anything.

## Publish Automation

The publish workflow:

- only reacts to `typescript-v*` tags
- validates that the tag matches the version in source control
- reruns package verification
- publishes to npm through pnpm with provenance enabled

One-time maintainer configuration is documented in `../../docs/release-setup.md`.

## Fallback Publishing

Local `pnpm publish` is not the normal path.

Only use a local fallback if GitHub Actions or trusted publishing is unavailable and a maintainer explicitly decides to bypass CI. If that happens:

- record the reason in the release issue or PR
- publish from the exact merged release commit
- create the same `typescript-vX.Y.Z` tag after the manual publish if the version was successfully released

## Post-Release Checklist

- Confirm the npm package page shows the new version.
- Smoke-test install if the change is high risk:

```bash
pnpm add @tiangong-lca/tidas-sdk@X.Y.Z
```

- Create or update GitHub release notes if useful for consumers.
- If the release is part of tracked `lca-workspace` delivery, complete the later submodule integration step.
