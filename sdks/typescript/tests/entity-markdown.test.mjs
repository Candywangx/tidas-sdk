import assert from 'node:assert/strict';
import test from 'node:test';
import sdk from '../src/index.ts';
const { TidasLifeCycleModel, TidasProcess } = sdk;

const uuid = 'f623219a-57c6-4c6a-a107-2396cfa8d714';
const timestamp = '2026-01-02T03:04:05.000Z';
const text = (en, zh) => [
  { '@xml:lang': 'en', '#text': en },
  { '@xml:lang': 'zh', '#text': zh },
];
const reference = (en, zh) => ({ 'common:shortDescription': text(en, zh) });
const classification = { 'common:classification': { 'common:class': [
  { '@level': '1', '#text': 'Electricity' },
  { '@level': '0', '#text': 'Energy' },
] } };
const administrativeInformation = {
  dataEntryBy: { 'common:timeStamp': timestamp },
  publicationAndOwnership: { 'common:dataSetVersion': '01.02.003' },
};

// These are deliberately small data containers: rendering is a pure view and does
// not imply that a partially authored dataset passes structural validation.
function modelInput() {
  return { lifeCycleModelDataSet: {
    lifeCycleModelInformation: {
      dataSetInformation: {
        'common:UUID': uuid,
        name: { baseName: text('Solar system', '太阳能系统'), mixAndLocationTypes: text('Grid mix', '电网组合'),
          treatmentStandardsRoutes: text('Rooftop', '屋顶'), functionalUnitFlowProperties: text('1 kWh', '1 千瓦时') },
        classificationInformation: structuredClone(classification),
        'common:synonyms': text('PV', '光伏'),
        'common:generalComment': text('A rooftop supply model.', '屋顶供电模型。'),
        referenceToResultingProcess: reference('Electricity supply', '电力供应'),
        referenceToExternalDocumentation: reference('Design report', '设计报告'),
      },
      quantitativeReference: { referenceToReferenceProcess: 2 },
      technology: {
        processes: { processInstance: [
          { '@dataSetInternalID': '10', '@multiplicationFactor': '2.50', referenceToProcess: reference('Transport', '运输') },
          { '@dataSetInternalID': '2', '@multiplicationFactor': '1', referenceToProcess: reference('Generation', '发电') },
        ] },
        referenceToDiagram: reference('System diagram', '系统图'),
      },
    },
    modellingAndValidation: { dataSourcesTreatmentEtc: { useAdviceForDataSet: text('Use for annual supply.', '用于年度供电。') } },
    administrativeInformation: structuredClone(administrativeInformation),
  } };
}

function processInput() {
  return { processDataSet: {
    processInformation: {
      dataSetInformation: {
        'common:UUID': uuid,
        name: { baseName: text('Electricity production', '电力生产'), mixAndLocationTypes: text('Regional mix', '区域组合'), treatmentStandardsRoutes: text('Solar', '太阳能') },
        classificationInformation: structuredClone(classification),
        'common:generalComment': text('Metered production.', '计量生产。'),
      },
      quantitativeReference: { referenceToReferenceFlow: '0', functionalUnitOrOther: text('One kWh delivered', '交付一千瓦时') },
      time: { 'common:referenceYear': 2025, 'common:dataSetValidUntil': 2030, 'common:timeRepresentativenessDescription': text('Annual average', '年度平均') },
      geography: { locationOfOperationSupplyOrProduction: { '@location': 'CN', descriptionOfRestrictions: text('Regional grid', '区域电网') } },
      technology: { technologicalApplicability: text('Grid connection', '并网'), technologyDescriptionAndIncludedProcesses: text('PV conversion', '光伏转换') },
    },
    modellingAndValidation: {
      LCIMethodAndAllocation: { typeOfDataSet: 'Unit process, single operation', LCIMethodPrinciple: 'Attributional', LCIMethodApproaches: 'Allocation - mass' },
      dataSourcesTreatmentAndRepresentativeness: { samplingProcedure: text('Monthly meters', '月度电表'), referenceToDataSource: reference('Meter report', '电表报告') },
    },
    administrativeInformation: structuredClone(administrativeInformation),
    exchanges: { exchange: [
      { '@dataSetInternalID': '2', exchangeDirection: 'Input', meanAmount: '0.25', referenceToFlowDataSet: reference('Silicon', '硅') },
      { '@dataSetInternalID': '0', exchangeDirection: 'Output', meanAmount: '1.000', referenceToFlowDataSet: reference('Electricity', '电力') },
      { '@dataSetInternalID': '1', exchangeDirection: 'Input', meanAmount: '3', referenceToFlowDataSet: reference('Sunlight', '阳光') },
    ] },
  } };
}

function assertPureRendering(entity, lang = 'en') {
  // Construction initializes the supplied object; this contract concerns only
  // the subsequent view operation, not constructor-input immutability.
  const before = JSON.stringify(entity.rawData);
  const first = entity.toMarkdown(lang);
  assert.equal(entity.toMarkdown(lang), first, 'rendering the same input must be deterministic');
  assert.equal(JSON.stringify(entity.rawData), before, 'rendering must preserve source values and ordering');
  assert.ok(!first.endsWith('\n'), 'rendered document has no trailing blank line');
  return first;
}

test('life-cycle model renders a complete English overview with ordered process references', () => {
  const model = new TidasLifeCycleModel(modelInput());
  assert.equal(assertPureRendering(model), [
    '# Solar system | Grid mix | Rooftop | 1 kWh', '', '**Entity:** Life Cycle Model',
    `**UUID:** \`${uuid}\``, '**Version:** 01.02.003', '**Reference Process:** Generation (ID 2)',
    '**Resulting Process:** Electricity supply', '**External Documentation:** Design report',
    '**Classification:** Energy > Electricity', '**Synonyms:** PV', '',
    '## Description', '', 'A rooftop supply model.', '', '## Use Advice', '', 'Use for annual supply.', '',
    '## Process Instances', '', '- ID 2: Generation ×1', '- ID 10: Transport ×2.5', '',
    '## Technology', '', 'Diagram: System diagram',
  ].join('\n'));
});

test('life-cycle model localizes title, advice, references and diagram together', () => {
  const model = new TidasLifeCycleModel(modelInput());
  const md = assertPureRendering(model, 'zh');
  for (const expected of ['# 太阳能系统 | 电网组合 | 屋顶 | 1 千瓦时', '**Reference Process:** 发电 (ID 2)',
    '**Resulting Process:** 电力供应', '**External Documentation:** 设计报告', '**Synonyms:** 光伏',
    '屋顶供电模型。', '用于年度供电。', '- ID 10: 运输 ×2.5', 'Diagram: 系统图']) assert.ok(md.includes(expected), expected);
  assert.ok(!md.includes('Solar system'));
  const fallback = assertPureRendering(model, 'fr');
  assert.equal(fallback.split('\n')[0], '# Solar system | 太阳能系统 | Grid mix | 电网组合 | Rooftop | 屋顶 | 1 kWh | 1 千瓦时');
  assert.ok(fallback.includes('**Reference Process:** Generation (ID 2)'));
  assert.ok(fallback.includes('A rooftop supply model.\n\n屋顶供电模型。'));
});

test('life-cycle model retains unresolved reference evidence and handles a single process', () => {
  const input = modelInput();
  const info = input.lifeCycleModelDataSet.lifeCycleModelInformation;
  info.quantitativeReference.referenceToReferenceProcess = 99;
  info.technology.processes.processInstance = { '@dataSetInternalID': '0', referenceToProcess: reference('Assembly', '组装') };
  const md = assertPureRendering(new TidasLifeCycleModel(input));
  assert.ok(md.includes('**Reference Process:** Reference process (ID 99)'));
  assert.ok(md.includes('## Process Instances\n\n- ID 0: Assembly'));
  assert.ok(!md.includes('Generation'));
});

test('empty life-cycle model initializes identity and serializable namespaces without invented content', () => {
  const model = new TidasLifeCycleModel();
  const dataset = model.lifeCycleModelDataSet;
  const id = dataset.lifeCycleModelInformation.dataSetInformation['common:UUID'];
  assert.match(id, /^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i);
  assert.equal(dataset['@xmlns'], 'http://eplca.jrc.ec.europa.eu/ILCD/LifeCycleModel/2017');
  assert.equal(dataset['@xmlns:common'], 'http://lca.jrc.it/ILCD/Common');
  assert.equal(dataset['@version'], '1.1');
  assert.ok(Number.isFinite(Date.parse(dataset.administrativeInformation.dataEntryBy['common:timeStamp'])));
  assert.equal(assertPureRendering(model), `# Life Cycle Model\n\n**Entity:** Life Cycle Model\n**UUID:** \`${id}\``);
  assert.notEqual(new TidasLifeCycleModel().lifeCycleModelDataSet.lifeCycleModelInformation.dataSetInformation['common:UUID'], id);
});

test('process overview resolves reference flow zero and renders all documented data sections', () => {
  const process = new TidasProcess(processInput());
  assert.equal(assertPureRendering(process), [
    '# Electricity production | Regional mix | Solar', '', '**Entity:** Process', `**UUID:** \`${uuid}\``,
    '**Version:** 01.02.003', '**Location:** CN', '**Reference Flow:** Electricity', '**Amount:** 1',
    '**Classification:** Energy > Electricity', '**Functional Unit:** One kWh delivered', '',
    '## Description', '', 'Metered production.', '', '## Time Coverage', '',
    'Reference Year: 2025 | Valid Until: 2030', 'Annual average', '', '## Geography', '', 'Regional grid', '',
    '## Technology', '', 'Grid connection\n\nPV conversion', '', '## Methodology', '',
    '**Data Set Type:** Unit process, single operation', '**LCI Method Principle:** Attributional', '**LCI Method Approach:** Allocation - mass', '',
    '## Data Sources', '', 'Monthly meters\n\nMeter report', '', '## Main Inputs', '', '- Sunlight: 3', '- Silicon: 0.25', '',
    '## Main Outputs', '', '- Electricity: 1',
  ].join('\n'));
});

test('process localizes independently of exchange order and preserves caller identity', () => {
  const process = new TidasProcess(processInput());
  const md = assertPureRendering(process, 'zh');
  for (const expected of ['# 电力生产 | 区域组合 | 太阳能', '**Reference Flow:** 电力', '**Functional Unit:** 交付一千瓦时',
    '计量生产。', '年度平均', '区域电网', '并网\n\n光伏转换', '月度电表\n\n电表报告', '- 阳光: 3', '- 电力: 1']) assert.ok(md.includes(expected), expected);
  assert.equal(process.processDataSet.processInformation.dataSetInformation['common:UUID'], uuid);
  assert.equal(process.processDataSet.administrativeInformation.dataEntryBy['common:timeStamp'], timestamp);
  assert.equal(process.toMarkdown(), process.toMarkdown('en'));
});

test('process missing reference and singleton exchange omit unsupported claims', () => {
  const input = processInput();
  input.processDataSet.processInformation.quantitativeReference.referenceToReferenceFlow = '99';
  input.processDataSet.exchanges.exchange = { '@dataSetInternalID': '7', exchangeDirection: 'Output', meanAmount: '0' };
  const md = assertPureRendering(new TidasProcess(input));
  assert.ok(!md.includes('**Reference Flow:**'));
  assert.ok(!md.includes('**Amount:**'));
  assert.ok(!md.includes('## Main Inputs'));
  assert.ok(md.includes('## Main Outputs\n\n- Flow 7: 0'));
});

test('empty process initializes identity and renders only available information', () => {
  const process = new TidasProcess();
  const dataset = process.processDataSet;
  const id = dataset.processInformation.dataSetInformation['common:UUID'];
  assert.match(id, /^[0-9a-f-]{36}$/i);
  assert.equal(dataset['@xmlns'], 'http://lca.jrc.it/ILCD/Process');
  assert.equal(dataset['@version'], '1.1');
  assert.ok(Number.isFinite(Date.parse(dataset.administrativeInformation.dataEntryBy['common:timeStamp'])));
  assert.equal(assertPureRendering(process), `# Process\n\n**Entity:** Process\n**UUID:** \`${id}\``);
});
