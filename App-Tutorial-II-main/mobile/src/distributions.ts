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
      ['high', 'Máximo b', '10'],
    ],
    help: '0 ≤ a < b ≤ 10. Dominio opcional: muestreo condicionado.',
  },
  {
    id: 'normal',
    label: 'Normal',
    kind: 'Continua',
    fields: [
      ['mean', 'Media μ', '5'],
      ['std', 'Desviación σ', '0.5'],
    ],
    help: '4 ≤ μ ≤ 6; 0.1 ≤ σ ≤ 0.8. Soporte real.',
  },
  {
    id: 'lognormal',
    label: 'LogNormal',
    kind: 'Continua',
    fields: [
      ['mu', 'μ — Log-location', '0'],
      ['sigma', 'σ — Log-scale', '0.25'],
    ],
    help: '−2 ≤ μ ≤ 0.6; 0.05 ≤ σ ≤ 0.35. ln(X) ~ Normal(μ, σ²); X > 0.',
  },
  {
    id: 'weibull',
    label: 'Weibull',
    kind: 'Continua',
    fields: [
      ['shape', 'Forma k', '2'],
      ['scale', 'Escala λ', '0.8'],
    ],
    help: 'Forma k entre 1 y 5; escala λ entre 0.1 y 0.8.',
  },
  {
    id: 'gamma',
    label: 'Gamma',
    kind: 'Continua',
    fields: [
      ['shape', 'Forma k', '5'],
      ['scale', 'Escala θ', '0.3'],
    ],
    help: 'Forma k entre 0.1 y 10; escala θ entre 0.01 y 0.3. Se usa escala, no tasa.',
  },
  {
    id: 'beta',
    label: 'Beta',
    kind: 'Continua',
    fields: [
      ['alpha', 'Alpha', '2'],
      ['beta', 'Beta', '2'],
    ],
    help: 'Alpha y beta entre 0.1 y 10. Soporte [0, 1].',
  },
  {
    id: 'exponential',
    label: 'Exponencial',
    kind: 'Continua',
    fields: [['rate', 'Tasa λ', '2']],
    help: 'Tasa λ entre 1.3 y 100. Media 1/λ. Es continua.',
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
    help: 'Hasta 10 valores numéricos únicos entre 0 y 10. Una probabilidad por valor; deben sumar 1.',
  },
  {
    id: 'generalized_poisson',
    label: 'Poisson generalizada',
    kind: 'Discreta',
    fields: [
      ['lam', 'Lambda', '1'],
      ['theta', 'Dispersión θ', '0.03'],
    ],
    help: 'Consul-Jain: 0.1 ≤ λ ≤ 1, 0 ≤ θ ≤ 0.05. Media λ/(1−θ).',
  },
  {
    id: 'zero_inflated_poisson',
    label: 'Poisson cero-inflada',
    kind: 'Discreta',
    fields: [
      ['lam', 'Lambda', '1'],
      ['pi', 'Probabilidad de cero estructural', '0.3'],
    ],
    help: '0.1 ≤ λ ≤ 1.5; 0 ≤ π ≤ 1. Mezcla de cero y Poisson.',
  },
  {
    id: 'logarithmic',
    label: 'Logarítmica',
    kind: 'Discreta',
    fields: [['p', 'Probabilidad p', '0.2']],
    help: '0.01 ≤ p ≤ 0.35. Serie logarítmica sobre enteros 1, 2, 3...',
  },
];
// prettier-ignore
export const PARAMETER_RANGES: Record<string, Record<string, [number, number]>> = {
  "uniform": {
    "low": [
      0,
      10
    ],
    "high": [
      0,
      10
    ]
  },
  "normal": {
    "mean": [
      4,
      6
    ],
    "std": [
      0.1,
      0.8
    ]
  },
  "lognormal": {
    "mu": [
      -2,
      0.6
    ],
    "sigma": [
      0.05,
      0.35
    ]
  },
  "weibull": {
    "shape": [
      1,
      5
    ],
    "scale": [
      0.1,
      0.8
    ]
  },
  "gamma": {
    "shape": [
      0.1,
      10
    ],
    "scale": [
      0.01,
      0.3
    ]
  },
  "beta": {
    "alpha": [
      0.1,
      10
    ],
    "beta": [
      0.1,
      10
    ]
  },
  "bernoulli": {
    "p": [
      0,
      1
    ]
  },
  "generalized_poisson": {
    "lam": [
      0.1,
      1
    ],
    "theta": [
      0,
      0.05
    ]
  },
  "exponential": {
    "rate": [
      1.3,
      100
    ]
  },
  "zero_inflated_poisson": {
    "lam": [
      0.1,
      1.5
    ],
    "pi": [
      0,
      1
    ]
  },
  "logarithmic": {
    "p": [
      0.01,
      0.35
    ]
  }
};
export const MAX_VARIABLES_PER_COMPONENT = 5;
export const MAX_CATEGORICAL_VALUES = 10;
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
  if (!/^X(?:[1-9]|1[0-5])$/.test(name))
    throw Error('Los nombres deben ser X1 a X15.');
  for (const [key, [lower, upper]] of Object.entries(
    PARAMETER_RANGES[d.id] || {},
  )) {
    const value = p[key];
    if (value < lower || value > upper)
      throw Error(`${key} debe estar entre ${lower} y ${upper}.`);
  }
  if (d.id === 'uniform' && p.low >= p.high)
    throw Error('El mínimo debe ser menor que el máximo.');
  if (d.id === 'categorical') {
    const v = params.values as number[],
      q = params.probabilities as number[];
    if (
      !v.length ||
      v.length > MAX_CATEGORICAL_VALUES ||
      v.length !== q.length ||
      new Set(v).size !== v.length ||
      v.some(x => x < 0 || x > 10) ||
      q.some(x => x < 0 || x > 1) ||
      Math.abs(q.reduce((a, b) => a + b, 0) - 1) > 1e-8
    )
      throw Error(
        'Categórica: de 1 a 10 valores únicos entre 0 y 10 y probabilidades que sumen 1.',
      );
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
