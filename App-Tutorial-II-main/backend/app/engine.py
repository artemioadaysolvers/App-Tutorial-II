"""Simulation kernel: Python standard library + NumPy ONLY. No eval or SymPy."""
import math
import re
from decimal import Decimal, ROUND_DOWN, localcontext
import numpy as np

N = 100
MAX_VARIABLES_PER_COMPONENT = 5
MAX_CATEGORICAL_VALUES = 10
RESULT_LIMIT = 1e100
PARAMETER_RANGES = {'uniform': {'low': [0, 10], 'high': [0, 10]},
 'normal': {'mean': [4, 6], 'std': [0.1, 0.8]},
 'lognormal': {'mu': [-2, 0.6], 'sigma': [0.05, 0.35]},
 'weibull': {'shape': [1, 5], 'scale': [0.1, 0.8]},
 'gamma': {'shape': [0.1, 10], 'scale': [0.01, 0.3]},
 'beta': {'alpha': [0.1, 10], 'beta': [0.1, 10]},
 'bernoulli': {'p': [0, 1]},
 'generalized_poisson': {'lam': [0.1, 1], 'theta': [0, 0.05]},
 'exponential': {'rate': [1.3, 100]},
 'zero_inflated_poisson': {'lam': [0.1, 1.5], 'pi': [0, 1]},
 'logarithmic': {'p': [0.01, 0.35]}}
PARAMS = {name: set(fields) for name, fields in PARAMETER_RANGES.items()}
PARAMS['categorical'] = {'values', 'probabilities'}

class Invalid(ValueError):
    pass

def keys(obj, required, optional=()):
    if type(obj) is not dict or not set(required) <= obj.keys() or obj.keys() - set(required) - set(optional):
        raise Invalid('Campos ausentes o desconocidos en el formato JSON.')

def number(x):
    if type(x) not in (int, float) or abs(x) > 1e9 or not math.isfinite(x):
        raise Invalid('Se requieren números finitos entre -1e9 y 1e9; no booleanos.')
    return float(x)

def validate_variable(v):
    keys(v, {'name', 'distribution', 'params'}, {'domain'})
    if type(v['name']) is not str or not re.fullmatch(r'X(?:[1-9]|1[0-5])', v['name']):
        raise Invalid('Los nombres deben ser X1 a X15.')
    d, p = v['distribution'], v['params']
    if type(d) is not str or d not in PARAMS:
        raise Invalid('Distribución desconocida.')
    keys(p, PARAMS[d])
    if d == 'categorical':
        a, b = p['values'], p['probabilities']
        if type(a) is not list or type(b) is not list or not 1 <= len(a) <= MAX_CATEGORICAL_VALUES or len(a) != len(b):
            raise Invalid('Categórica: entre 1 y 10 valores con una probabilidad por valor.')
        a, b = [number(x) for x in a], [number(x) for x in b]
        if len(set(a)) != len(a) or any(not 0 <= x <= 10 for x in a):
            raise Invalid('Categórica: valores únicos entre 0 y 10.')
        if any(not 0 <= x <= 1 for x in b) or abs(sum(b) - 1) > 1e-8:
            raise Invalid('Probabilidades entre 0 y 1 que sumen 1.')
    else:
        for key, (lower, upper) in PARAMETER_RANGES[d].items():
            value = number(p[key])
            if not lower <= value <= upper:
                raise Invalid(f'{d}: {key} debe estar entre {lower} y {upper}.')
        if d == 'uniform' and p['low'] >= p['high']:
            raise Invalid('Uniforme: mínimo menor que máximo.')
    dom = v.get('domain', {})
    keys(dom, set(), {'min', 'max'})
    for value in dom.values():
        number(value)
    if 'min' in dom and 'max' in dom and dom['min'] >= dom['max']:
        raise Invalid('Dominio: mínimo menor que máximo.')

ARITY = {'add': 2, 'sub': 2, 'mul': 2, 'div': 2, 'pow': 2,
         'neg': 1, 'abs': 1, 'sqrt': 1, 'log': 1, 'exp': 1, 'sin': 1, 'cos': 1}

def validate_ast(node, names, depth=0, budget=None):
    if budget is None:
        budget = [0]
    budget[0] += 1
    if depth > 20 or budget[0] > 127 or type(node) is not dict:
        raise Invalid('Expresión demasiado compleja (127 nodos, profundidad 20).')
    if set(node) == {'const'}:
        number(node['const'])
    elif set(node) == {'var'}:
        if type(node['var']) is not str or node['var'] not in names:
            raise Invalid('Variable desconocida en la expresión.')
    else:
        keys(node, {'op', 'args'})
        op, args = node['op'], node['args']
        if type(op) is not str or op not in ARITY or type(args) is not list or len(args) != ARITY[op]:
            raise Invalid('Operador o número de argumentos inválido.')
        for a in args:
            validate_ast(a, names, depth + 1, budget)

def validate(payload):
    if type(payload) is not dict or type(payload.get('version')) is not int or payload['version'] not in (1, 2):
        raise Invalid('Solo protocolos 1 y 2.')
    field = 'expression' if payload['version'] == 1 else 'expressions'
    keys(payload, {'version', 'title', 'variables', field, 'samples'})
    if type(payload['samples']) is not int or payload['samples'] != N:
        raise Invalid('Exactamente 100 realizaciones conjuntas.')
    if type(payload['title']) is not str or not 1 <= len(payload['title'].strip()) <= 80:
        raise Invalid('Título obligatorio de hasta 80 caracteres.')
    expressions = components(payload)
    if type(expressions) is not list or not 1 <= len(expressions) <= 3:
        raise Invalid('Define entre 1 y 3 expresiones, en orden X, Y, Z.')
    vs = payload['variables']
    limit = MAX_VARIABLES_PER_COMPONENT * len(expressions)
    if type(vs) is not list or not 1 <= len(vs) <= limit:
        raise Invalid(f'Debe haber entre 1 y {limit} variables en este experimento; máximo 5 distintas por componente.')
    for v in vs:
        validate_variable(v)
    names = {v['name'] for v in vs}
    if len(names) != len(vs):
        raise Invalid('Los nombres de variables deben ser únicos.')
    used = set()
    for expression in expressions:
        validate_ast(expression, names)
        refs = references(expression)
        if not refs:
            raise Invalid('Cada componente debe contener una variable aleatoria.')
        if len(refs) > MAX_VARIABLES_PER_COMPONENT:
            raise Invalid('Cada componente puede usar como máximo 5 variables aleatorias distintas.')
        used.update(refs)
    if names != used:
        raise Invalid('Todas las variables definidas deben utilizarse en al menos un componente.')
    return payload

def references(node):
    if 'var' in node:
        return {node['var']}
    return set().union(*(references(a) for a in node.get('args', [])))


def final_results(payload, results):
    """Validate final components and truncate decimal representations toward zero.

    This boundary never accepts or persists base-variable realizations. Decimal
    avoids binary multiplication errors such as trunc(1.001 * 1000) == 1000.
    """
    if type(results) is not list or len(results) != N * len(components(payload)):
        raise Invalid('Se requieren exactamente 100 resultados por componente, en una lista plana.')
    out = []
    with localcontext() as ctx:
        ctx.prec = 128  # Includes 1e100 and three fractional decimal places.
        for value in results:
            if type(value) not in (int, float) or abs(value) > RESULT_LIMIT or not math.isfinite(value):
                raise Invalid('Resultado no finito o fuera de rango (máximo 1e100).')
            truncated = float(Decimal(str(value)).quantize(Decimal('0.001'), rounding=ROUND_DOWN))
            out.append(0.0 if truncated == 0 else truncated)
    return out


def components(payload):
    return [payload['expression']] if payload['version'] == 1 else payload['expressions']

def raw(rng, d, p, size):
    if d == 'uniform': return rng.uniform(p['low'], p['high'], size)
    if d == 'normal': return rng.normal(p['mean'], p['std'], size)
    if d == 'lognormal': return rng.lognormal(p['mu'], p['sigma'], size)
    if d == 'weibull': return p['scale'] * rng.weibull(p['shape'], size)
    if d == 'gamma': return rng.gamma(p['shape'], p['scale'], size)
    if d == 'beta': return rng.beta(p['alpha'], p['beta'], size)
    if d == 'bernoulli': return rng.binomial(1, p['p'], size)
    if d == 'categorical':
        probs = np.array(p['probabilities'], dtype=float)
        return rng.choice(p['values'], size=size, p=probs / probs.sum())
    if d == 'exponential': return rng.exponential(1 / p['rate'], size)
    if d == 'zero_inflated_poisson':
        return np.where(rng.random(size) < p['pi'], 0, rng.poisson(p['lam'], size))
    if d == 'logarithmic': return rng.logseries(p['p'], size)
    # Consul-Jain generalized Poisson, nonnegative dispersion.
    # Poisson immigrants, Poisson(theta) offspring; sum all generations.
    generation = rng.poisson(p['lam'], size)
    total = generation.copy()
    for _ in range(10000):
        if not np.any(generation): return total
        generation = rng.poisson(p['theta'] * generation)
        total += generation
    raise Invalid('No convergió Poisson generalizada.')

def draw(rng, variable):
    dom = variable.get('domain', {})
    accepted = []
    count = 0
    for _ in range(2000):
        a = np.asarray(raw(rng, variable['distribution'], variable['params'], N), dtype=float)
        if not np.all(np.isfinite(a)):
            raise Invalid('La distribución generó valores no finitos; revisa parámetros.')
        a = a[(a >= dom.get('min', -np.inf)) & (a <= dom.get('max', np.inf))]
        accepted.extend(a.tolist())
        count += len(a)
        if count >= N: return np.array(accepted[:N])
    raise Invalid('El dominio no tiene suficiente masa: amplíalo o revisa los parámetros.')

def evaluate(n, values):
    if 'const' in n: return np.full(N, n['const'], dtype=float)
    if 'var' in n: return values[n['var']]
    args = [evaluate(a, values) for a in n['args']]
    operations = {'add': np.add, 'sub': np.subtract, 'mul': np.multiply,
                  'div': np.divide, 'pow': np.power, 'neg': np.negative,
                  'abs': np.abs, 'sqrt': np.sqrt, 'log': np.log,
                  'exp': np.exp, 'sin': np.sin, 'cos': np.cos}
    with np.errstate(all='ignore'):
        result = operations[n['op']](*args)
    if not np.all(np.isfinite(result)) or np.any(np.abs(result) > 1e100):
        raise Invalid('Expresión indefinida o desbordada (división por cero, log, raíz o potencia).')
    return result

def simulate(payload, seed=None):
    validate(payload)
    rng = np.random.default_rng(seed)
    values = {v['name']: draw(rng, v) for v in payload['variables']}
    # Shared draws across all components preserve dependence, e.g. (X1, 2*X1).
    result = np.column_stack([evaluate(expr, values) for expr in components(payload)])
    if not np.all(np.isfinite(result)) or np.any(np.abs(result) > 1e100):
        raise Invalid('Resultado fuera de rango: revisa la distribución o expresión (máximo 1e100).')
    # Only expression outputs cross the process boundary. Variable draws are discarded.
    # Flat row-major layout: x0,y0,z0,x1,y1,z1,... (Firestore disallows nested arrays).
    return final_results(payload, result.astype(float).ravel().tolist())
