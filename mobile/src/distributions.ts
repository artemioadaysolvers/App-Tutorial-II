export type Distribution = {
  id: string;
  label: string;
  kind: string;
  fields: [string, string, string][];
  help: string;
};
export const distributions: Distribution[] = [
  {
    id: 'uniform',
    label: 'Uniforme',
    kind: 'Continua',
    fields: [
      ['low', 'Mínimo a', '0'],
      ['high', 'Máximo b', '1'],
    ],
    help: 'a < b. Soporte [a, b].',
  },
  {
    id: 'normal',
    label: 'Normal',
    kind: 'Continua',
    fields: [
      ['mean', 'Media μ', '0'],
      ['std', 'Desviación σ', '1'],
    ],
    help: 'σ > 0. Soporte real.',
  },
  {
    id: 'lognormal',
    label: 'LogNormal',
    kind: 'Continua',
    fields: [
      ['mean', 'Media del logaritmo', '0'],
      ['sigma', 'Desviación del logaritmo', '1'],
    ],
    help: 'σ > 0. Parámetros de log(X); X > 0.',
  },
  {
    id: 'weibull',
    label: 'Weibull',
    kind: 'Continua',
    fields: [
      ['shape', 'Forma k', '2'],
      ['scale', 'Escala λ', '1'],
    ],
    help: 'Forma y escala positivas. Soporte X ≥ 0.',
  },
  {
    id: 'gamma',
    label: 'Gamma',
    kind: 'Continua',
    fields: [
      ['shape', 'Forma k', '2'],
      ['scale', 'Escala θ', '1'],
    ],
    help: 'Forma y escala positivas. Se usa escala, no tasa.',
  },
  {
    id: 'beta',
    label: 'Beta',
    kind: 'Continua',
    fields: [
      ['alpha', 'Alpha', '2'],
      ['beta', 'Beta', '2'],
    ],
    help: 'Alpha y beta positivos. Soporte [0, 1].',
  },
  {
    id: 'exponential',
    label: 'Exponencial',
    kind: 'Continua',
    fields: [['rate', 'Tasa λ', '1']],
    help: 'λ > 0. Media 1/λ. Es continua.',
  },
  {
    id: 'bernoulli',
    label: 'Bernoulli',
    kind: 'Discreta',
    fields: [['p', 'Probabilidad de 1', '0.5']],
    help: '0 ≤ p ≤ 1. Valores 0 y 1.',
  },
  {
    id: 'categorical',
    label: 'Categórica',
    kind: 'Discreta',
    fields: [
      ['values', 'Valores separados por coma', '0, 1, 2'],
      ['probabilities', 'Probabilidades en el mismo orden', '0.2, 0.3, 0.5'],
    ],
    help: 'Hasta 50 valores numéricos únicos. Una probabilidad por valor; deben sumar 1.',
  },
  {
    id: 'generalized_poisson',
    label: 'Poisson generalizada',
    kind: 'Discreta',
    fields: [
      ['lam', 'Lambda', '3'],
      ['theta', 'Dispersión θ', '0.2'],
    ],
    help: 'Consul-Jain: 0 < λ ≤ 100, 0 ≤ θ ≤ 0.9. Media λ/(1-θ). Dispersión no negativa.',
  },
  {
    id: 'zero_inflated_poisson',
    label: 'Poisson cero-inflada',
    kind: 'Discreta',
    fields: [
      ['lam', 'Lambda', '3'],
      ['pi', 'Probabilidad de cero estructural', '0.3'],
    ],
    help: 'λ > 0, 0 ≤ π ≤ 1. Mezcla de cero y Poisson (que también puede producir ceros).',
  },
  {
    id: 'logarithmic',
    label: 'Logarítmica',
    kind: 'Discreta',
    fields: [['p', 'Probabilidad p', '0.5']],
    help: '0 < p < 1. Serie logarítmica sobre enteros 1, 2, 3...',
  },
];
export type Variable = {
  name: string;
  distribution: string;
  params: Record<string, number | number[]>;
  domain?: { min?: number; max?: number };
};
export function numeric(text: string): number {
  if (!text.trim()) throw Error('Completa todos los números.');
  const n = Number(text);
  if (!Number.isFinite(n) || Math.abs(n) > 1e9)
    throw Error('Números finitos con punto decimal y magnitud hasta 1e9.');
  return n;
}
export function makeVariable(
  name: string,
  d: Distribution,
  fields: Record<string, string>,
  min: string,
  max: string,
): Variable {
  const params: Record<string, number | number[]> = {};
  d.fields.forEach(([k]) => {
    params[k] = ['values', 'probabilities'].includes(k)
      ? fields[k].split(',').map(numeric)
      : numeric(fields[k]);
  });
  const p = params as Record<string, number>;
  for (const k of [
    'std',
    'sigma',
    'shape',
    'scale',
    'alpha',
    'beta',
    'rate',
    'lam',
  ])
    if (k in p && p[k] <= 0) throw Error(`${k} debe ser positivo.`);
  if (d.id === 'uniform' && p.low >= p.high)
    throw Error('El mínimo debe ser menor que el máximo.');
  if (
    'p' in p &&
    !(d.id === 'bernoulli' ? p.p >= 0 && p.p <= 1 : p.p > 0 && p.p < 1)
  )
    throw Error('Probabilidad fuera de rango.');
  if ('pi' in p && (p.pi < 0 || p.pi > 1))
    throw Error('Pi debe estar entre 0 y 1.');
  if (
    d.id === 'generalized_poisson' &&
    (p.lam > 100 || p.theta < 0 || p.theta > 0.9)
  )
    throw Error('Lambda hasta 100; theta entre 0 y 0.9.');
  if (d.id === 'categorical') {
    const v = params.values as number[],
      q = params.probabilities as number[];
    if (
      !v.length ||
      v.length > 50 ||
      v.length !== q.length ||
      new Set(v).size !== v.length ||
      q.some(x => x < 0) ||
      Math.abs(q.reduce((a, b) => a + b, 0) - 1) > 1e-8
    )
      throw Error('Revisa valores únicos y probabilidades que sumen 1.');
  }
  const domain: { min?: number; max?: number } = {};
  if (min.trim()) domain.min = numeric(min);
  if (max.trim()) domain.max = numeric(max);
  if (
    domain.min !== undefined &&
    domain.max !== undefined &&
    domain.min >= domain.max
  )
    throw Error('Dominio: mínimo menor que máximo.');
  return { name, distribution: d.id, params, domain };
}
