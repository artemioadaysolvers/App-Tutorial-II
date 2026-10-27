import fs from 'node:fs';
import ts from 'typescript';
import assert from 'node:assert/strict';
const modules = new Map();
async function load(file) {
  if (modules.has(file)) return import(modules.get(file));
  const text = fs.readFileSync(
    new URL('../src/' + file + '.ts', import.meta.url),
    'utf8',
  );
  let js = ts.transpileModule(text, {
    compilerOptions: {
      module: ts.ModuleKind.ES2022,
      target: ts.ScriptTarget.ES2022,
    },
  }).outputText;
  if (file === 'expression') {
    await load('distributions');
    js = js
      .replaceAll(
        "'./distributions'",
        JSON.stringify(modules.get('distributions')),
      )
      .replaceAll(
        '"./distributions"',
        JSON.stringify(modules.get('distributions')),
      );
  }
  const url =
    'data:text/javascript;base64,' + Buffer.from(js).toString('base64');
  modules.set(file, url);
  return import(url);
}
const { parseExpression } = await load('expression');
const { histogram } = await load('histogram');
const { distributions, makeVariable } = await load('distributions');
assert.deepEqual(parseExpression('-X1^2 + 3*X2', ['X1', 'X2']), {
  op: 'add',
  args: [
    { op: 'neg', args: [{ op: 'pow', args: [{ var: 'X1' }, { const: 2 }] }] },
    { op: 'mul', args: [{ const: 3 }, { var: 'X2' }] },
  ],
});
assert.deepEqual(parseExpression('X1^2^3', ['X1']), {
  op: 'pow',
  args: [{ var: 'X1' }, { op: 'pow', args: [{ const: 2 }, { const: 3 }] }],
});
assert.equal(parseExpression('sqrt(X1)', ['X1']).op, 'sqrt');
for (const bad of [
  'X11',
  'X1;alert(1)',
  'X1.foo',
  'X1 X1',
  '2+2',
  'sqrt(X1',
  'X1+',
  'X1**2',
])
  assert.throws(() => parseExpression(bad, ['X1']));
for (const bins of [1, 2, 10, 50]) {
  const h = histogram(
    Array.from({ length: 100 }, (_, i) => i),
    bins,
  );
  assert.ok(Math.abs(h.frequencies.reduce((a, b) => a + b, 0) - 1) < 1e-12);
  assert.ok(h.frequencies.every(x => x >= 0));
}
assert.deepEqual(histogram([0, 1, 2, 3], 2).frequencies, [0.5, 0.5]);
assert.equal(
  histogram(Array(100).fill(4), 10).frequencies.reduce((a, b) => a + b, 0),
  1,
);
assert.throws(() => histogram([1], 0));
assert.equal(distributions.length, 12);
for (const d of distributions)
  makeVariable(
    'X1',
    d,
    Object.fromEntries(d.fields.map(([k, , v]) => [k, v])),
    '',
    '',
  );
assert.throws(() =>
  makeVariable(
    'X1',
    distributions.find(d => d.id === 'categorical'),
    { values: '1,2', probabilities: '.1,.1' },
    '',
    '',
  ),
);
console.log(
  'PASS: parser, precedence, rejected expressions, 12 distributions, relative histogram and constant data.',
);
const { jointHistogram } = await load('jointHistogram');
for (const dimensions of [1, 2, 3]) {
  const flat = Array.from({ length: 100 }, (_, i) =>
    Array.from({ length: dimensions }, (_, d) => (d === 2 ? 7 : i * (d + 1))),
  ).flat();
  for (const bins of [1, dimensions === 1 ? 50 : dimensions === 2 ? 12 : 8]) {
    const h = jointHistogram(flat, dimensions, bins);
    assert.ok(
      Math.abs(h.cells.reduce((s, c) => s + c.frequency, 0) - 1) < 1e-12,
    );
    assert.ok(
      h.cells.every(
        c =>
          c.indices.length === dimensions &&
          c.indices.every(i => i >= 0 && i < bins),
      ),
    );
  }
}
const correlated = jointHistogram(
  [0, 0, 1, 1, ...Array(98).fill([1, 1]).flat()],
  2,
  2,
);
assert.equal(correlated.cells.length, 2);
assert.equal(correlated.cells.find(c => c.indices[0] === 1).indices[1], 1);
assert.throws(() => jointHistogram(Array(200).fill(1), 3, 5));
assert.throws(() => jointHistogram(Array(300).fill(1), 3, 9));
console.log(
  'PASS: joint histogram 1D/2D/3D, correlations, 100/200/300 values, boundaries and relative sums.',
);
const {
  PARAMETER_RANGES,
  MAX_CATEGORICAL_VALUES,
  MAX_VARIABLES_PER_COMPONENT,
} = await load('distributions');
const { referencedVariables } = await load('expression');
assert.equal(MAX_CATEGORICAL_VALUES, 10);
assert.equal(MAX_VARIABLES_PER_COMPONENT, 5);
const allNames = Array.from({ length: 15 }, (_, i) => `X${i + 1}`);
assert.equal(
  referencedVariables(parseExpression('X1 + X1 + X2', allNames)).size,
  2,
);
assert.equal(
  referencedVariables(parseExpression('X11 + X12 + X13 + X14 + X15', allNames))
    .size,
  5,
);
assert.throws(
  () => parseExpression('X1+X2+X3+X4+X5+X6', allNames),
  /5 variables/,
);
assert.throws(() => parseExpression('X16', allNames));
for (const d of distributions) {
  if (d.id === 'categorical') continue;
  const defaults = Object.fromEntries(d.fields.map(([k, , v]) => [k, v]));
  for (const [key, [lo, hi]] of Object.entries(PARAMETER_RANGES[d.id])) {
    for (const value of [
      lo - Math.max(1, Math.abs(lo)) * 1e-6,
      hi + Math.max(1, Math.abs(hi)) * 1e-6,
    ])
      assert.throws(() =>
        makeVariable('X1', d, { ...defaults, [key]: String(value) }, '', ''),
      );
    if (d.id !== 'uniform')
      for (const value of [lo, hi])
        makeVariable('X15', d, { ...defaults, [key]: String(value) }, '', '');
  }
}
const categorical = distributions.find(d => d.id === 'categorical');
makeVariable(
  'X1',
  categorical,
  {
    values: '0,1,2,3,4,5,6,7,8,9',
    probabilities: Array(10).fill('0.1').join(','),
  },
  '',
  '',
);
for (const fields of [
  {
    values: '0,1,2,3,4,5,6,7,8,9,10',
    probabilities: Array(11)
      .fill(String(1 / 11))
      .join(','),
  },
  { values: '-1,1', probabilities: '0.5,0.5' },
  { values: '1,11', probabilities: '0.5,0.5' },
  { values: '1,1', probabilities: '0.5,0.5' },
])
  assert.throws(() => makeVariable('X1', categorical, fields, '', ''));
assert.deepEqual(
  distributions.find(d => d.id === 'lognormal').fields.map(([key]) => key),
  ['mu', 'sigma'],
);
console.log(
  'PASS: all parameter ranges, log-location/log-scale, categorical <=10, X1..X15 and <=5 distinct references/component.',
);
