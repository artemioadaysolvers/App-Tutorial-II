"""Simulation kernel: Python standard library + NumPy ONLY. No eval or SymPy."""
import math
import re
import numpy as np

N = 100
PARAMS = {
    'uniform': {'low', 'high'}, 'normal': {'mean', 'std'},
    'lognormal': {'mean', 'sigma'}, 'weibull': {'shape', 'scale'},
    'gamma': {'shape', 'scale'}, 'beta': {'alpha', 'beta'},
    'bernoulli': {'p'}, 'categorical': {'values', 'probabilities'},
    'generalized_poisson': {'lam', 'theta'}, 'exponential': {'rate'},
    'zero_inflated_poisson': {'lam', 'pi'}, 'logarithmic': {'p'},
}

class Invalid(ValueError):
    pass

def keys(obj, required, optional=()):
    if type(obj) is not dict or not set(required) <= obj.keys() or obj.keys() - set(required) - set(optional):
        raise Invalid('Campos ausentes o desconocidos en el formato JSON.')

def number(x):
    if type(x) not in (int, float) or not math.isfinite(x) or abs(x) > 1e9:
        raise Invalid('Se requieren números finitos entre -1e9 y 1e9; no booleanos.')
    return float(x)

def validate_variable(v):
    keys(v, {'name', 'distribution', 'params'}, {'domain'})
    if type(v['name']) is not str or not re.fullmatch(r'X[1-3]', v['name']):
        raise Invalid('Los nombres deben ser X1 a X3.')
    d, p = v['distribution'], v['params']
    if type(d) is not str or d not in PARAMS:
        raise Invalid('Distribución desconocida.')
    keys(p, PARAMS[d])
    if d == 'categorical':
        a, b = p['values'], p['probabilities']
        if type(a) is not list or type(b) is not list or not 1 <= len(a) <= 50 or len(a) != len(b):
            raise Invalid('Categórica: entre 1 y 50 valores con una probabilidad por valor.')
        a, b = [number(x) for x in a], [number(x) for x in b]
        if len(set(a)) != len(a) or any(x < 0 for x in b) or abs(sum(b) - 1) > 1e-8:
            raise Invalid('Valores únicos y probabilidades no negativas que sumen 1.')
    else:
        for value in p.values():
            number(value)
        positive = {'std', 'sigma', 'shape', 'scale', 'alpha', 'beta', 'rate', 'lam'}
        if any(p[k] <= 0 for k in p.keys() & positive):
            raise Invalid('Escalas, formas, tasas y lambda deben ser positivas.')
        if d == 'uniform' and p['low'] >= p['high']:
            raise Invalid('Uniforme: mínimo menor que máximo.')
        if 'p' in p and not (0 <= p['p'] <= 1 if d == 'bernoulli' else 0 < p['p'] < 1):
            raise Invalid('Probabilidad fuera del intervalo permitido.')
        if 'pi' in p and not 0 <= p['pi'] <= 1:
            raise Invalid('Inflación de ceros pi entre 0 y 1.')
        if d == 'generalized_poisson' and not (0 < p['lam'] <= 100 and 0 <= p['theta'] <= .9):
            raise Invalid('Poisson generalizada: 0 < lambda <= 100 y 0 <= theta <= 0.9.')
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
    vs = payload['variables']
    if type(vs) is not list or not 1 <= len(vs) <= 3:
        raise Invalid('Debe haber entre 1 y 3 variables aleatorias en total.')
    for v in vs:
        validate_variable(v)
    names = {v['name'] for v in vs}
    if len(names) != len(vs):
        raise Invalid('Los nombres de variables deben ser únicos.')
    expressions = components(payload)
    if type(expressions) is not list or not 1 <= len(expressions) <= 3:
        raise Invalid('Define entre 1 y 3 expresiones, en orden X, Y, Z.')
    def references(n):
        return {n['var']} if 'var' in n else set().union(*(references(a) for a in n.get('args', [])))
    for expression in expressions:
        validate_ast(expression, names)
        if not references(expression):
            raise Invalid('Cada componente debe contener una variable aleatoria.')
    return payload

def components(payload):
    return [payload['expression']] if payload['version'] == 1 else payload['expressions']

def raw(rng, d, p, size):
    if d == 'uniform': return rng.uniform(p['low'], p['high'], size)
    if d == 'normal': return rng.normal(p['mean'], p['std'], size)
    if d == 'lognormal': return rng.lognormal(p['mean'], p['sigma'], size)
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
    return result.astype(float).ravel().tolist()
