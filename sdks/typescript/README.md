# TIDAS TypeScript SDK

TypeScript SDK for the TIDAS (TianGong Life Cycle Assessment data format)
contracts, runtime validation, XML conversion, and package-level parity tools.

Published package: [@tiangong-lca/tidas-sdk](https://www.npmjs.com/package/@tiangong-lca/tidas-sdk).
Read the installed package metadata or npm registry for the current version.

Exact Node.js 24.19.0 and the root-pinned `pnpm@11.24.0` are required for
development and release verification.

## Installation

```bash
pnpm add @tiangong-lca/tidas-sdk
```

## Public entry points

| Entry point                         | Purpose                                      |
| ----------------------------------- | -------------------------------------------- |
| `@tiangong-lca/tidas-sdk`           | Combined public API                          |
| `@tiangong-lca/tidas-sdk/core`      | Entity classes and current factory functions |
| `@tiangong-lca/tidas-sdk/types`     | Generated TIDAS TypeScript types             |
| `@tiangong-lca/tidas-sdk/schemas`   | Generated Zod schemas and validation helpers |
| `@tiangong-lca/tidas-sdk/contracts` | TIDAS context and methodology contracts      |
| `@tiangong-lca/tidas-sdk/parity`    | Package-directory JSON Schema validation     |
| `@tiangong-lca/tidas-sdk/xml`       | XML parsing and serialization                |
| `@tiangong-lca/tidas-sdk/tools`     | Directory conversion and runtime assets      |
| `@tiangong-lca/tidas-sdk/utils`     | General SDK utilities                        |

Every entry point is exercised through CJS, ESM, and TypeScript declaration
consumer tests before release.

### Public rule definitions

```typescript
import { getTidasPublicRules } from '@tiangong-lca/tidas-sdk/contracts';

const selection = getTidasPublicRules('flow');
if (selection.status === 'covered') {
  for (const rule of selection.rules) console.log(rule.id, rule.locations);
}
```

The result is the versioned public-definition layer: stable identity, dataset/location, applicability, normative level, source references, and examples. It intentionally excludes product profiles, severity/phase policy, blocker defaults, waivers, and action authorization. Valid dataset kinds without reviewed public definitions return `not-covered`. The former `getTidasRuntimeRuleset` compatibility API and its two `runtime_rulesets` files are not part of this SDK package; execution policy belongs to consumers such as CLI.

## Current factory API

The maintained entity factories are:

```typescript
import {
  createContact,
  createFlow,
  createFlowProperty,
  createLCIAMethod,
  createLifeCycleModel,
  createProcess,
  createSource,
  createUnitGroup,
} from '@tiangong-lca/tidas-sdk/core';
```

Each entity also has `FromJSON` and plural `Batch` variants. Multilingual
fields use the standard TIDAS item or item-array representation; the SDK does
not expose `setText`/`getText` methods.

```typescript
import { createContact } from '@tiangong-lca/tidas-sdk/core';

const contact = createContact();
const information =
  contact.contactDataSet.contactInformation.dataSetInformation;

information['common:name'] = [
  { '@xml:lang': 'en', '#text': 'Example data steward' },
];

const result = contact.validate();
if (!result.success) {
  console.error(result.error.issues);
}
```

A complete, valid contact draft is maintained at
[`examples/01-basic-usage/contact-draft.ts`](./examples/01-basic-usage/contact-draft.ts).

## Schema validation

```typescript
import {
  ContactSchema,
  parseWithZod,
  validateWithZod,
} from '@tiangong-lca/tidas-sdk/schemas';

const result = validateWithZod(value, ContactSchema);
const parsed = parseWithZod(jsonText, ContactSchema);
```

Generated schemas come directly from the asset-lock-selected Draft-07 JSON
Schema documents. Named domain overlays preserve CAS checks, multilingual
validation codes, `common:other`, required multilingual values, Flow name
conditions, and review conditions. Generation fails when it encounters a
validation keyword or overlay location that is not explicitly supported.

For stable programmatic error handling, entity callers should prefer
`validateEnhanced()` and consume normalized `validationIssues` rather than
parsing Zod message text.

## TypeScript 0.6 validation migration

Version 0.6.0 pins runtime `zod` to exact `4.6.7` and aligns native string bounds
and asserted date-time validation with the locked public Draft-07 specification.
Python remains 0.3.0; the immutable specification/tools inputs are unchanged.

| Input or diagnostic | Frozen Zod 4.4.3 baseline | Qualified 0.6.0 / Zod 4.6.7 |
| --- | --- | --- |
| 251 emoji in a maxLength 500 field | Rejected as 502 UTF-16 units | Accepted as 251 Unicode code points |
| 501 emoji in that field | Rejected; actualLength 1002 | Rejected; actualLength 501 |
| `2020-01-01T06:15Z` or `2020-01-01T06:15+08:00` | Accepted | Rejected; RFC 3339 requires seconds |
| `2020-01-01T06:15:00Z` and second/fraction values with a valid offset | Accepted | Accepted; parsed strings preserved |

Normalized string `params.actualLength` now uses Unicode code points, matching
the native validator and JSON Schema bounds. A combining sequence such as
`e` plus a combining accent counts as two; emoji joined by a zero-width joiner
still contain several code points. This is not a grapheme-cluster count.
Array length diagnostics still count array elements. Existing custom language,
CAS and other named overlay codes/paths remain covered; no legacy UTF-16 or
minute-only datetime exception is introduced.

The package minor is a deliberate pre-1.0 migration: `^0.5.x` does not select
0.6.0. However, published 0.5.1 declares **`zod: ^4.4.3`**, which already permits
4.6.x in an unlocked installation. The new version boundary does not
retroactively freeze that published line. Audit the actual resolved dependency
and lockfile when comparing old consumers; the old column above specifically
means a frozen 4.4.3 runtime. New 0.6.0's exact dependency binds the qualified
semantics. No previous release/tag is rewritten and no consuming repository is
upgraded automatically. Before adopting it, run the consumer's real data cases,
review string limits, and supply timestamp seconds according to its data.

## Package parity validation

```typescript
import { validatePackageDir } from '@tiangong-lca/tidas-sdk/parity';

const report = validatePackageDir('/path/to/tidas-package');
if (!report.ok) {
  console.error(report.issues);
}
```

## XML and directory conversion

```typescript
import { datasetFromXml, datasetToXml } from '@tiangong-lca/tidas-sdk/xml';
import { convertDirectory } from '@tiangong-lca/tidas-sdk/tools';

const dataset = datasetFromXml(xmlPayload);
const xml = datasetToXml(dataset);

await convertDirectory('./input', './output', { toXml: true });
await convertDirectory('./eilcd-data', './tidas-output', { toXml: false });
```

Database export, ZIP publishing, and S3 workflows remain owned by
[`tidas-tools`](https://github.com/tiangong-lca/tidas-tools).

## Development

```bash
# Run from the repository root with the exact pnpm version in package.json.
pnpm install --frozen-lockfile
pnpm --filter @tiangong-lca/tidas-sdk lint
pnpm --filter @tiangong-lca/tidas-sdk typecheck
pnpm --filter @tiangong-lca/tidas-sdk test
pnpm --filter @tiangong-lca/tidas-sdk check:examples
pnpm --filter @tiangong-lca/tidas-sdk build
```

The root `pnpm-workspace.yaml` and `pnpm-lock.yaml` are the only workspace and
dependency-lock sources. The package uses a single `typescript@7.x` compiler
track. Oxlint performs type-aware linting, Node 24.19.0 runs tests through `tsx`, and
the published tarball does not carry compiler, generator, lint, or test tooling
into consumers.

Useful commands:

```bash
pnpm --filter @tiangong-lca/tidas-sdk generate-types
pnpm --filter @tiangong-lca/tidas-sdk generate-schemas
pnpm --filter @tiangong-lca/tidas-sdk verify:schema-generation-parity
pnpm --filter @tiangong-lca/tidas-sdk test:coverage
pnpm --filter @tiangong-lca/tidas-sdk format:check
```

For generator parity, build the baseline before editing the generator. The
default baseline is `dist/schemas`; `TIDAS_ZOD_BASELINE_DIR` and
`TIDAS_ZOD_CANDIDATE_DIR` can select explicit artifacts. Automatic candidate
output is always cleaned.

The maintained examples are executable contracts:

- `examples/01-basic-usage/contact-draft.ts`
- `examples/02-xml-roundtrip/xml-roundtrip.ts`
- `examples/test-imports.ts`

Run all of them with `pnpm --filter tidas-sdk-examples check`.

## Release

The normal release path is documented in [RELEASE.md](./RELEASE.md). Before a
release PR, run the repository wrapper from the repository root:

```bash
./scripts/ci/verify-typescript-package.sh
```

After merge, the exact merged commit is tagged as `typescript-vX.Y.Z` and the
repository-owned Trusted Publishing workflow publishes it.

## Repository documentation

- [Repository contract](../../AGENTS.md)
- [Validation guide](../../docs/agents/repo-validation.md)
- [Release setup](../../docs/release-setup.md)
- [Upstream automation](../../docs/upstream-automation.md)

## License

MIT — see [LICENSE](./LICENSE).

### Allocation/reference semantic analysis (0.5.1)

`analyzeProcessSemantics` is a separate, synchronous, side-effect-free API, exported
from the package root and `/core`. Run structural validation and semantic analysis
as distinct checks; `strict` and generated schemas keep their existing behavior.

```typescript
import { analyzeProcessSemantics, PROCESS_SEMANTIC_PROFILE } from '@tiangong-lca/tidas-sdk';
const result = analyzeProcessSemantics(process, {
  flows: [{ uuid: flowId, version: '01.00.000', type: 'Waste flow', contentHash: flowHash }],
});
// Admission requires both result.valid and result.complete, plus structural proof.
// result.validationIssues has normalized code/path/severity/params/message/rawCode.
// result.interpretations exposes every validated explicit target and qref coefficient.
```

The API executes consumer policy `tidas.process-allocation-reference.v1`, not a
new public specification. Every explicit target must resolve uniquely within the
same Process. Input and Output targets with exact Product or Waste Flow evidence
are eligible; Elementary and Other targets are invalid. The target-type check is
not applied to unrelated exchanges or qrefs. Supply exact UUID/version evidence
in `flows`, or `resolveFlow(uuid, version)`. The resolver is called at most once
per distinct applicable exact identity; exceptions are unresolved. There is no
implicit network or filesystem access. Duplicate evidence, absent evidence,
invalid types, inexact references, and version mismatches cannot become a pass.
The caller verifies evidence content and binds the process hash, Flow hashes,
package/source identity, profile and tolerance to its acceptance receipt;
`contentHash` records supplied provenance and is not computed or verified here.

Coverage is `passed`, `invalid`, `unresolved`, or `not-applicable` for each check.
`complete` is false if applicable evidence is unresolved; `valid` is false for
invalid or unresolved findings. A resolved semantic finding can be complete and
invalid. No explicit allocation means no target-type evidence is required.
Quantitative references resolve scalar or repeated `Reference flow(s)` IDs
uniquely, including Input references. Valid Functional unit, Other parameter and
Production period preserve their language-tagged basis. Multiple references and
non-flow bases have `calculationApplicability: 'unsupported'` for the selected
single-reference calculation capability without becoming semantic errors.

Compatibility is interpreted without modifying authored data:

| Declaration | Interpretation |
| --- | --- |
| Absent allocation | `undeclared`; coefficient 1 for each declared qref |
| Scalar `allocation: {}` | `legacy-scalar-empty`; coefficient 1 |
| Empty array or `[{}]` | Invalid malformed vector |
| Explicit target vector | Unique eligible targets, finite fractions 0–100, sum 100 |
| Explicit vector omitting a selected qref | Valid SparseZero coefficient 0 |
| Targetless full declaration on a non-Output exchange | Bounded `legacy-targetless-full`: exactly 100 or the retained `100%` spelling, and one uniquely resolved qref |
| Any targetless Output declaration | Process-wide `legacy-output-share`; all such declarations must be on Outputs and sum 100 (70% + 30% supported) |
| Targetless fraction declarations plus any explicit vector | Invalid mixed modes |
| Mixed targeted and targetless entries in one vector | Invalid mixed modes |

When no Output-share declaration exists, each targetless declaration uses the
bounded full fallback. Undeclared/scalar-empty declarations do not select a
compatibility mode. In Output-share mode, the selected qref share applies to the
whole inventory, including undeclared and scalar-empty exchanges; a qref without
a declared legacy share retains the historical coefficient 1. Output and Input
targetless fraction declarations cannot be mixed. Full decimal tokens or finite
numbers are parsed after trimming surrounding whitespace, without coercion,
hexadecimal, Infinity or NaN. Explicit vector fractions reject percent suffixes;
legacy Output shares accept a trailing percent sign. Non-Output full fallback
accepts exactly 100 or the special trimmed `100%` spelling, without sum tolerance. Exponent notation is supported by this policy; structural `Perc` validity
is checked separately. Absolute percentage-point sum tolerance is `0.0010000001` (the retained three-decimal Perc boundary).
`interpretations.allocations` preserves all validated explicit target IDs and
fractions, and provides the full inferred compatibility projection for Output-share
and full-fallback modes. Inferred legacy targets retain historical compatibility
without claiming an explicit target-type check: a generator that materializes an
explicit vector must validate that final vector with exact Flow evidence and prove
coefficient preservation for every declared qref. In `legacy-output-share` mode,
`allocations` is the declared legacy share vector, not an unconditional rewrite
recipe: a qref omitted from those shares has the historical coefficient 1, while
an explicit vector omitting that qref has SparseZero coefficient 0. A generator
must report unsupported applicability when it cannot preserve that distinction
without choosing or redirecting modelling targets. `coefficients` projects each
declared qref, independently of direction.
An invalid/unresolved vector has no accepted interpretation. Consumers must check
the aggregate result before using any projection.

The shared `tests/fixtures/process-semantics.v1.json` is consumed independently
by TypeScript and native Rust Toolkit tests. Source qualification does not claim
registry publication or downstream runtime adoption. Python API is unchanged.
