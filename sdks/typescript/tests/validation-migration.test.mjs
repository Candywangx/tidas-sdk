import assert from 'node:assert/strict';
import test from 'node:test';
import { z } from 'zod';
import sdk from '../src/index.ts';
import {
  dateTimeSchema,
  StringSchema,
  STSchema,
} from '../src/schemas/tidas_data_types.schema.ts';

const { TidasContact, ValidationUtils } = sdk;
const timestampPath = ['contactDataSet', 'administrativeInformation', 'dataEntryBy', 'common:timeStamp'];
const namePath = ['contactDataSet', 'contactInformation', 'dataSetInformation', 'common:name'];

function contactInput() {
  const reference = {
    '@type': 'source data set',
    '@refObjectId': 'a97a0155-0234-4b87-b4ce-a45da52f2a40',
    '@version': '03.00.003',
    '@uri': '../source.xml',
    'common:shortDescription': { '@xml:lang': 'en', '#text': 'ILCD' },
  };
  return { contactDataSet: {
    contactInformation: { dataSetInformation: {
      'common:UUID': '5e9ce347-252e-4a1b-9ee9-904bf1737b45',
      'common:shortName': { '@xml:lang': 'en', '#text': 'Contact' },
      'common:name': { '@xml:lang': 'en', '#text': 'Contact' },
      classificationInformation: { 'common:classification': { 'common:class': {
        '@level': '0', '@classId': '1', '#text': 'Group of organisations, project',
      } } },
    } },
    administrativeInformation: {
      dataEntryBy: { 'common:timeStamp': '2020-01-01T06:15:00Z', 'common:referenceToDataSetFormat': reference },
      publicationAndOwnership: { 'common:dataSetVersion': '01.01.000', 'common:referenceToOwnershipOfDataSet': { ...reference, '@type': 'contact data set' } },
    },
  } };
}

function validate(edit) {
  const input = contactInput();
  edit?.(input);
  return new TidasContact(input, { mode: 'strict' }).validateEnhanced();
}

function lengthIssue(path, maximum, actualLength) {
  return {
    code: 'string_too_long', path,
    params: { exact: undefined, inclusive: true, maximum, origin: 'string', actualLength },
    severity: 'error', message: `Too big: expected string to have <=${maximum} characters`, rawCode: 'too_big',
  };
}

function datetimeIssue(path = timestampPath) {
  return { code: 'invalid_format', path, params: { format: 'datetime' }, severity: 'error', message: 'Invalid ISO datetime', rawCode: 'invalid_format' };
}

test('strict shipped entities use code-point bounds for localized singletons and arrays', () => {
  assert.equal(validate().success, true, 'the complete entity fixture must start valid');
  for (const array of [false, true]) {
    for (const count of [250, 251, 500]) {
      const text = '😀'.repeat(count);
      const result = validate((input) => {
        const item = { '@xml:lang': 'en', '#text': text };
        input.contactDataSet.contactInformation.dataSetInformation['common:name'] = array ? [item] : item;
      });
      assert.equal(result.success, true, `${array ? 'array' : 'singleton'} with ${count} code points`);
      const parsed = result.data.contactDataSet.contactInformation.dataSetInformation['common:name'];
      assert.equal((array ? parsed[0] : parsed)['#text'], text);
    }
    const result = validate((input) => {
      const item = { '@xml:lang': 'en', '#text': '😀'.repeat(501) };
      input.contactDataSet.contactInformation.dataSetInformation['common:name'] = array ? [item] : item;
    });
    assert.equal(result.success, false);
    assert.deepEqual(result.validationIssues, [lengthIssue([...namePath, ...(array ? [0] : []), '#text'], 500, 501)]);
  }
});

test('shipped scalar bounds distinguish Unicode code points from UTF16 and graphemes', () => {
  for (const [schema, valid, invalid, maximum, actualLength] of [
    [StringSchema, '😀'.repeat(500), '😀'.repeat(501), 500, 501],
    [StringSchema, '中'.repeat(500), '中'.repeat(501), 500, 501],
    [StringSchema, 'e\u0301'.repeat(250), 'e\u0301'.repeat(251), 500, 502],
    [StringSchema, '👩‍🔬'.repeat(166), '👩‍🔬'.repeat(167), 500, 501],
    [STSchema, '😀'.repeat(1000), '😀'.repeat(1001), 1000, 1001],
  ]) {
    assert.deepEqual(schema.parse(valid), valid);
    const result = schema.safeParse(invalid);
    assert.equal(result.success, false);
    assert.deepEqual(ValidationUtils.normalizeIssues(result.error.issues, invalid), [lengthIssue([], maximum, actualLength)]);
  }
  assert.equal(StringSchema.safeParse('').success, false);
  assert.equal(StringSchema.safeParse('😀').success, true);
});

test('minimum string diagnostics count code points while array diagnostics retain element counts', () => {
  const text = '😀';
  const string = z.string().min(2).safeParse(text);
  assert.equal(string.success, false);
  assert.deepEqual(ValidationUtils.normalizeIssues(string.error.issues, text), [{
    code: 'string_too_short', path: [],
    params: { exact: undefined, inclusive: true, minimum: 2, origin: 'string', actualLength: 1 },
    severity: 'error', message: 'Too small: expected string to have >=2 characters', rawCode: 'too_small',
  }]);
  for (const [schema, value, code, bound] of [
    [z.array(z.string()).max(1), ['😀', 'a'], 'array_too_large', { maximum: 1 }],
    [z.array(z.string()).min(2), ['😀'], 'array_too_small', { minimum: 2 }],
  ]) {
    const result = schema.safeParse(value);
    assert.equal(result.success, false);
    const [issue] = ValidationUtils.normalizeIssues(result.error.issues, value);
    assert.equal(issue.code, code);
    assert.equal(issue.params.actualLength, value.length);
    assert.equal(issue.params.origin, 'array');
    for (const [key, expected] of Object.entries(bound)) assert.equal(issue.params[key], expected);
  }
});

test('scalar and actual entity datetime fields require seconds and preserve valid offset/fraction values', () => {
  for (const timestamp of ['2020-01-01T06:15:00Z', '2020-01-01T06:15:00+08:00', '2020-01-01T06:15:00.123456Z']) {
    assert.equal(dateTimeSchema.parse(timestamp), timestamp);
    const result = validate((input) => { input.contactDataSet.administrativeInformation.dataEntryBy['common:timeStamp'] = timestamp; });
    assert.equal(result.success, true);
    assert.equal(result.data.contactDataSet.administrativeInformation.dataEntryBy['common:timeStamp'], timestamp);
  }
  for (const timestamp of ['2020-01-01T06:15Z', '2020-01-01T06:15+08:00', '2020-01-01T06:15', '2020-01-01T06:15:00+0800', '2020-02-30T06:15:00Z', '2020-01-01T25:15:00Z']) {
    const scalar = dateTimeSchema.safeParse(timestamp);
    assert.equal(scalar.success, false);
    assert.deepEqual(ValidationUtils.normalizeIssues(scalar.error.issues, timestamp), [datetimeIssue([])]);
    const result = validate((input) => { input.contactDataSet.administrativeInformation.dataEntryBy['common:timeStamp'] = timestamp; });
    assert.equal(result.success, false);
    assert.deepEqual(result.validationIssues, [datetimeIssue()]);
  }
});

test('combined strict diagnostics retain language code/path/order alongside the new datetime rejection', () => {
  const result = validate((input) => {
    input.contactDataSet.contactInformation.dataSetInformation['common:name'] = { '@xml:lang': 'en', '#text': '中文' };
    input.contactDataSet.administrativeInformation.dataEntryBy['common:timeStamp'] = '2020-01-01T06:15Z';
  });
  assert.equal(result.success, false);
  assert.deepEqual(result.validationIssues, [{
    code: 'localized_text_en_must_not_contain_chinese_character', path: [...namePath, '#text'], params: undefined,
    severity: 'error', message: "@xml:lang value 'en' must not contain Chinese characters", rawCode: 'custom',
  }, datetimeIssue()]);
});
