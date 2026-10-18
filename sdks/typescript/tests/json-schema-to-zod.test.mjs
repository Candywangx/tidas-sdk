import assert from 'node:assert/strict';
import test from 'node:test';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { pathToFileURL } from 'node:url';

import { JsonSchemaToZod } from '../scripts/json-schema-to-zod.ts';
import { replaceExportedSchema } from '../scripts/schema-postprocess.ts';

test('orders local definitions by dependency and external imports deterministically', () => {
  const schema = {
    $defs: {
      Root: {
        type: 'object',
        required: ['local', 'zExternal', 'beta', 'alpha'],
        properties: {
          local: { $ref: '#/$defs/Leaf' },
          zExternal: { $ref: './zeta.json#/$defs/Zed' },
          beta: { $ref: './alpha.json#/$defs/Beta' },
          alpha: { $ref: './alpha.json#/$defs/Alpha' },
        },
      },
      Leaf: { type: 'string' },
    },
  };

  const rendered = new JsonSchemaToZod(
    'dependency-fixture.json',
    schema
  ).renderModule();

  assert.deepEqual(rendered.exportNames, ['LeafSchema', 'RootSchema']);
  assert.ok(
    rendered.content.indexOf('export const LeafSchema') <
      rendered.content.indexOf('export const RootSchema'),
    'a local dependency must be declared before the schema that references it'
  );
  assert.deepEqual(
    rendered.content.split('\n').filter((line) => line.startsWith('import ')),
    [
      "import { z } from 'zod';",
      "import { AlphaSchema, BetaSchema } from './alpha.schema';",
      "import { ZedSchema } from './zeta.schema';",
    ]
  );
  assert.match(
    rendered.content,
    /export const RootSchema = z\.object\(\{local: LeafSchema, zExternal: ZedSchema, beta: BetaSchema, alpha: AlphaSchema\}\);/
  );
});

test('renders required and optional fields with structural constraints', () => {
  const schema = {
    type: 'object',
    required: ['name', 'tags', 'count'],
    properties: {
      name: {
        type: 'string',
        minLength: 2,
        maxLength: 8,
        pattern: '^[a-z]+$',
      },
      note: { type: 'string' },
      tags: {
        type: 'array',
        items: { type: 'string' },
        minItems: 1,
        maxItems: 3,
      },
      count: {
        type: 'number',
        minimum: 0,
        maximum: 10,
        exclusiveMinimum: -1,
        exclusiveMaximum: 11,
        multipleOf: 2,
      },
    },
  };

  const { content } = new JsonSchemaToZod(
    'constraints.json',
    schema
  ).renderModule();

  assert.match(
    content,
    /name: z\.string\(\)\.min\(2\)\.max\(8\)\.regex\(\/\^\[a-z\]\+\$\/\)/
  );
  assert.match(content, /note: z\.string\(\)\.optional\(\)/);
  assert.match(content, /tags: z\.array\(z\.string\(\)\)\.min\(1\)\.max\(3\)/);
  assert.match(
    content,
    /count: z\.number\(\)\.min\(0\)\.max\(10\)\.gt\(-1\)\.lt\(11\)\.multipleOf\(2\)/
  );
});

test('renders enum, const, anyOf, and allOf without permissive fallbacks', () => {
  const schema = {
    type: 'object',
    required: ['mode', 'fixed', 'choice', 'combined'],
    properties: {
      mode: { enum: ['alpha', 'beta'] },
      fixed: { const: 42 },
      choice: { anyOf: [{ type: 'string' }, { type: 'number' }] },
      combined: {
        allOf: [{ type: 'string', minLength: 1 }, { maxLength: 5 }],
      },
    },
  };

  const { content } = new JsonSchemaToZod(
    'composition.json',
    schema
  ).renderModule();

  assert.match(
    content,
    /mode: z\.union\(\[z\.literal\("alpha"\), z\.literal\("beta"\)\]\)/
  );
  assert.match(content, /fixed: z\.literal\(42\)/);
  assert.match(content, /choice: z\.union\(\[z\.string\(\), z\.number\(\)\]\)/);
  assert.match(
    content,
    /combined: z\.intersection\(z\.string\(\)\.min\(1\), z\.string\(\)\.max\(5\)\)/
  );
  assert.doesNotMatch(content, /z\.unknown\(\)/);
});

test('combines const and enum with their sibling validation constraints', () => {
  const { content } = new JsonSchemaToZod('literal_siblings.json', {
    type: 'object',
    properties: {
      fixed: { type: 'integer', const: 2, minimum: 2 },
      mode: { type: 'string', enum: ['alpha'], minLength: 3 },
    },
  }).renderModule();

  assert.match(
    content,
    /fixed: z\.intersection\(z\.literal\(2\), z\.number\(\)\.int\(\)\.min\(2\)\)/
  );
  assert.match(
    content,
    /mode: z\.intersection\(z\.literal\("alpha"\), z\.string\(\)\.min\(3\)\)/
  );
});

test('throws for a not-only schema instead of accepting unknown input', () => {
  assert.throws(
    () =>
      new JsonSchemaToZod('unsupported.json', {
        not: { type: 'string' },
      }).renderModule(),
    /unsupported\.json#: not requires a required-only constraint or the CommonOther\/LocalizedText domain overlay/
  );
});

test('renders the same input identically on repeated calls', () => {
  const schema = {
    $defs: {
      Root: {
        type: 'object',
        required: ['local', 'external'],
        properties: {
          local: { $ref: '#/$defs/Leaf' },
          external: { $ref: './shared.json#/$defs/Shared' },
        },
      },
      Leaf: {
        anyOf: [{ const: 'leaf' }, { type: 'number', minimum: 1 }],
      },
    },
  };
  const renderer = new JsonSchemaToZod('determinism.json', schema);

  const first = renderer.renderModule();
  const second = renderer.renderModule();

  assert.deepEqual(second, first);
  assert.deepEqual(
    new JsonSchemaToZod('determinism.json', schema).renderModule(),
    first
  );
});

test('combines object siblings with anyOf and preserves exact oneOf semantics', () => {
  const { content } = new JsonSchemaToZod('composition_siblings.json', {
    type: 'object',
    properties: { kind: { type: 'string' } },
    required: ['kind'],
    anyOf: [
      {
        type: 'object',
        properties: { left: { const: true } },
        required: ['left'],
      },
      {
        type: 'object',
        properties: { right: { const: true } },
        required: ['right'],
      },
    ],
    oneOf: [
      { type: 'object', required: ['left'] },
      { type: 'object', required: ['right'] },
    ],
  }).renderModule();

  assert.match(content, /z\.object\(\{kind: z\.string\(\)\}\)/);
  assert.match(content, /z\.union\(\[/);
  assert.match(content, /jsonSchemaOneOf\(\[/);
  assert.match(content, /z\.intersection\(/);
});

test('renders integer, JSON-deep uniqueness, formats, tuple, and dependencies', () => {
  const { content } = new JsonSchemaToZod('active-keywords.json', {
    type: 'object',
    properties: {
      count: { type: 'integer' },
      createdAt: { type: 'string', format: 'date-time' },
      email: { type: 'string', format: 'email' },
      uri: { type: 'string', format: 'uri' },
      values: {
        type: 'array',
        items: { type: 'object', additionalProperties: true },
        uniqueItems: true,
      },
      tuple: {
        type: 'array',
        items: [{ const: 'first' }, { type: 'integer' }],
        additionalItems: false,
      },
    },
    dependencies: {
      count: {
        type: 'object',
        required: ['createdAt'],
      },
    },
  }).renderModule();

  assert.match(content, /count: z\.number\(\)\.int\(\)/);
  assert.match(content, /z\.iso\.datetime\(\{ offset: true \}\)/);
  assert.match(content, /z\.email\(\)/);
  assert.match(content, /z\.url\(\)/);
  assert.match(content, /withJsonSchemaUniqueItems\(/);
  assert.match(content, /jsonSchemaTuple\(/);
  assert.match(content, /withJsonSchemaDependencies\(/);
});

test('renders additionalProperties policy explicitly', () => {
  const strict = new JsonSchemaToZod('strict.json', {
    type: 'object',
    properties: { known: { type: 'string' } },
    additionalProperties: false,
  }).renderModule().content;
  const typed = new JsonSchemaToZod('typed.json', {
    type: 'object',
    properties: { known: { type: 'string' } },
    additionalProperties: { type: 'integer' },
  }).renderModule().content;

  assert.match(strict, /\.strict\(\)/);
  assert.match(typed, /\.catchall\(z\.number\(\)\.int\(\)\)/);
});

test('fails closed for unknown and unhandled validation keywords', () => {
  assert.throws(
    () =>
      new JsonSchemaToZod('future.json', {
        type: 'string',
        minContains: 1,
      }).renderModule(),
    /future\.json#: unsupported JSON Schema keyword minContains/
  );
  assert.throws(
    () =>
      new JsonSchemaToZod('pattern-properties.json', {
        type: 'object',
        patternProperties: { '^x-': { type: 'string' } },
      }).renderModule(),
    /patternProperties is only supported by the CommonOther domain overlay/
  );
  assert.throws(
    () =>
      new JsonSchemaToZod('unknown-format.json', {
        type: 'string',
        format: 'hostname',
      }).renderModule(),
    /unsupported JSON Schema format hostname/
  );
});

test('preserves boolean if/then/else schemas instead of treating false as absent', () => {
  const { content } = new JsonSchemaToZod('boolean-conditional.json', {
    if: true,
    then: false,
    else: true,
  }).renderModule();

  assert.match(
    content,
    /withJsonSchemaConditional\(z\.unknown\(\), z\.unknown\(\), z\.never\(\), z\.unknown\(\)\)/
  );
});

test('fails when a domain overlay target is absent', () => {
  assert.throws(
    () =>
      replaceExportedSchema(
        "import { z } from 'zod';\n",
        'MissingSchema',
        'export const MissingSchema = z.string();'
      ),
    /Could not replace missing generated schema MissingSchema/
  );
});


test('comments do not change validation and conflicting aliases render a negated required constraint', () => {
  const original = new JsonSchemaToZod('comment.json', { type: 'string' }).renderModule();
  const annotated = new JsonSchemaToZod('comment.json', { type: 'string', $comment: 'Maintainer-only text' }).renderModule();
  assert.equal(annotated.content, original.content);
  assert.throws(() => new JsonSchemaToZod('comment.json', { type: 'string', $comment: 1 }).renderModule(), /comment must be a string/);
  const aliases = new JsonSchemaToZod('alias.json', { not: { required: ['canonical', 'legacy'] } }).renderModule();
  assert.match(aliases.content, /jsonSchemaNotRequired\(\["canonical","legacy"\]\)/);
});

test('regenerated string bounds and date-time use native public-spec semantics', async () => {
  const input = { type: 'object', required: ['text', 'timestamp'], properties: {
    text: { type: 'string', minLength: 2, maxLength: 3 },
    timestamp: { type: 'string', format: 'date-time' },
  } };
  const first = new JsonSchemaToZod('migration.json', input).renderModule();
  assert.deepEqual(new JsonSchemaToZod('migration.json', input).renderModule(), first);
  assert.match(first.content, /z\.string\(\)\.min\(2\)\.max\(3\)/);
  assert.match(first.content, /z\.iso\.datetime\(\{ offset: true \}\)/);
  const directory = fs.mkdtempSync(path.join(os.tmpdir(), 'tidas-generated-migration-'));
  try {
    const modulePath = path.join(directory, 'generated.mjs');
    fs.writeFileSync(modulePath, first.content.replace("'zod'", JSON.stringify(import.meta.resolve('zod'))));
    const generated = (await import(pathToFileURL(modulePath).href))[first.exportNames[0]];
    const valid = { text: '😀😀😀', timestamp: '2020-01-01T06:15:00Z' };
    assert.deepEqual(generated.parse(valid), valid);
    assert.equal(generated.safeParse({ ...valid, text: '😀' }).success, false);
    assert.equal(generated.safeParse({ ...valid, timestamp: '2020-01-01T06:15Z' }).success, false);
  } finally {
    fs.rmSync(directory, { recursive: true, force: true });
  }
});
