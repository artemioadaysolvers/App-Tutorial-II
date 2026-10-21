import fs from 'node:fs';
import ts from 'typescript';
import assert from 'node:assert/strict';
async function load(file) {
  const text = fs.readFileSync(
    new URL('../src/' + file + '.ts', import.meta.url),
    'utf8',
  );
  const js = ts.transpileModule(text, {
    compilerOptions: {
      module: ts.ModuleKind.ES2022,
      target: ts.ScriptTarget.ES2022,
    },
  }).outputText;
  return import(
    'data:text/javascript;base64,' + Buffer.from(js).toString('base64')
  );
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
