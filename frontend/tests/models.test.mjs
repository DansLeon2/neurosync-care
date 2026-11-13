import test from 'node:test';
import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import ts from 'typescript';

// Use the project's compiler and node:test; no extra test runtime or DOM imitation.
async function load(path) {
  const source = await readFile(new URL(path, import.meta.url), 'utf8');
  const { outputText } = ts.transpileModule(source, { compilerOptions: { target: ts.ScriptTarget.ES2022, module: ts.ModuleKind.ES2022 } });
  return import('data:text/javascript;base64,' + Buffer.from(outputText).toString('base64'));
}
const { CircularBuffer } = await load('../src/features/telemetry/buffer.ts');
const { linePath, selectedValue } = await load('../src/features/telemetry/chartModel.ts');
const { sensorReadings, cranialPosition } = await load('../src/features/neuromap/sensorModel.ts');
const { modelInstructions } = await load('../src/features/session/preparationContent.ts');
const point = (ms, value, overrides = {}) => ({ timestamp: new Date(ms).toISOString(), bands: { alpha: value }, pow: { AF3: { alpha: value } }, source: 'SIMULATED', pow_unit: 'u.a.', ...overrides });

test('circular history keeps newest data in chronological order and releases cleared values', () => {
  const buffer = new CircularBuffer(3);
  for (let i=0;i<10;i++) buffer.push(i);
  assert.deepEqual(buffer.snapshot(), [7,8,9]);
  const copy = buffer.snapshot(); copy.push(100);
  assert.deepEqual(buffer.snapshot(), [7,8,9]);
  buffer.clear(); assert.deepEqual(buffer.snapshot(), []);
  buffer.push(11); assert.deepEqual(buffer.snapshot(), [11]);
});
test('line never connects across missing data, time gaps, unit or source changes', () => {
  const points = [point(0,1), point(125,2), point(250,null), point(375,3), point(2000,4), point(2125,5,{source:'REAL_EMOTIV'})];
  const path = linePath(points, 'alpha', 'AF3', value => value, value => value);
  assert.equal((path.match(/M/g)||[]).length, 4);
  assert.equal((path.match(/L/g)||[]).length, 1);
  assert.equal(selectedValue(point(0,null), 'alpha', 'AF3'), null);
  assert.equal(selectedValue(point(0,9), 'alpha', 'O1'), null);
});
test('sensor view keeps original values and never substitutes unknown contact', () => {
  const frame = { pow: { AF3: { alpha: 7 } }, quality: {}, contact: { AF3: 3 } };
  const readings = sensorReadings({ sensors: [{id:'AF3',x:-.27,y:.74}, {id:'AF4',x:.27,y:.74}] }, frame, 'alpha', 'power', 10);
  assert.equal(readings[0].value, 7); assert.equal(readings[0].quality, null);
  assert.equal(readings[1].value, null); assert.equal(readings[1].contact, null);
  assert.notEqual(readings[0].color, readings[1].color);
  assert.ok(cranialPosition(-.27,.74).every(Number.isFinite));
});
test('preparation distinguishes polymer sensors and does not invent a procedure for unknown models', () => {
  assert.match(modelInstructions('INSIGHT')[1], /no usa los fieltros/);
  assert.match(modelInstructions('EPOCX')[1], /solución indicada/);
  assert.match(modelInstructions('OTHER')[1], /No se aplica automáticamente/);
});
