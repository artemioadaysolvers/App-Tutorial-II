import copy
import math
import time
import unittest
import numpy as np
from app.engine import PARAMS, Invalid, raw, simulate, validate, final_results, references
from app.runner import run_limited

PARAMETERS = {
    'uniform': {'low': 0, 'high': 1}, 'normal': {'mean': 5, 'std': .5},
    'lognormal': {'mu': 0, 'sigma': .25}, 'weibull': {'shape': 2, 'scale': .8},
    'gamma': {'shape': 5, 'scale': .3}, 'beta': {'alpha': 2, 'beta': 5},
    'bernoulli': {'p': .3}, 'categorical': {'values': [2, 4], 'probabilities': [.25, .75]},
    'generalized_poisson': {'lam': 1, 'theta': .03}, 'exponential': {'rate': 2},
    'zero_inflated_poisson': {'lam': 1, 'pi': .3}, 'logarithmic': {'p': .2},
}

def spec(d='normal'):
    return {'version': 1, 'title': 'Test', 'samples': 100,
            'variables': [{'name': 'X1', 'distribution': d, 'params': PARAMETERS[d].copy()}],
            'expression': {'var': 'X1'}}

def sum_ast(names):
    node = {'var':names[0]}
    for name in names[1:]:node={'op':'add','args':[node,{'var':name}]}
    return node

def sleeping_worker(conn, payload):
    time.sleep(10)

class EngineTests(unittest.TestCase):
    def test_five_variables_per_component_up_to_fifteen_total(self):
        for dimensions in (1, 2, 3):
            p = spec('uniform'); p.pop('expression')
            p.update(version=2, expressions=[]); p['variables'] = []
            for d in range(dimensions):
                names = [f'X{i}' for i in range(d*5+1, d*5+6)]
                p['variables'].extend({'name':name,'distribution':'uniform','params':{'low':0,'high':1}} for name in names)
                p['expressions'].append(sum_ast(names))
            self.assertEqual(len(simulate(p, seed=42)), 100*dimensions)
        for name in ('X0', 'X16', 'X01', 'X1x'):
            p=spec();p['variables'][0]['name']=name;p['expression']={'var':name}
            with self.assertRaises(Invalid):validate(p)

    def test_vector_components_share_draws_and_have_exact_layout(self):
        for dimensions in (1, 2, 3):
            p=spec();p.pop('expression');p['version']=2
            p['expressions']=[{'var':'X1'}, {'op':'mul','args':[{'const':2},{'var':'X1'}]}, {'op':'sub','args':[{'var':'X1'},{'var':'X1'}]}][:dimensions]
            values=np.array(simulate(p, seed=42)).reshape(100,dimensions)
            self.assertEqual(values.size,100*dimensions)
            if dimensions>=2:np.testing.assert_allclose(values[:,1],2*values[:,0],atol=.002,rtol=0)
            if dimensions==3:np.testing.assert_array_equal(values[:,2],np.zeros(100))

    def test_invalid_vector_schemas_and_component_failure(self):
        for expressions in ([], [{'var':'X1'}]*4, None, [{'var':'X9'}], [{'const':1}]):
            p=spec();p.pop('expression');p.update(version=2,expressions=expressions)
            with self.assertRaises(Invalid):validate(p)
        p=spec();p.pop('expression');p.update(version=2,expressions=[{'var':'X1'}, {'op':'div','args':[{'var':'X1'},{'const':0}]}])
        with self.assertRaises(Invalid):simulate(p)

    def test_all_distributions_exactly_100_finite_outputs(self):
        self.assertEqual(set(PARAMS), set(PARAMETERS))
        for d in PARAMETERS:
            with self.subTest(d=d):
                out = simulate(spec(d), seed=42)
                self.assertEqual(len(out), 100)
                self.assertTrue(np.isfinite(out).all())

    def test_theoretical_means(self):
        means = {'uniform': .5, 'normal': 5, 'lognormal': math.exp(.25**2/2),
                 'weibull': .8*math.gamma(1.5), 'gamma': 1.5, 'beta': 2/7,
                 'bernoulli': .3, 'categorical': 3.5, 'generalized_poisson': 1/.97,
                 'exponential': .5, 'zero_inflated_poisson': .7,
                 'logarithmic': -.2/(.8*math.log(.8))}
        for d in means:
            with self.subTest(d=d):
                draws = raw(np.random.default_rng(7), d, PARAMETERS[d], 100000)
                tolerance = max(.015, 6 * np.std(draws)/math.sqrt(len(draws)))
                self.assertAlmostEqual(float(np.mean(draws)), means[d], delta=tolerance)
        g = raw(np.random.default_rng(8), 'generalized_poisson', PARAMETERS['generalized_poisson'], 100000)
        self.assertAlmostEqual(float(np.var(g)), 1/.97**3, delta=.05)

    def test_repeated_variable_uses_same_realization(self):
        p = spec(); p['expression'] = {'op': 'sub', 'args': [{'var': 'X1'}, {'var': 'X1'}]}
        self.assertEqual(simulate(p), [0.] * 100)

    def test_multi_variable_expression(self):
        p = spec('uniform'); p['variables'].append({'name': 'X2', 'distribution': 'bernoulli', 'params': {'p': 1}})
        p['expression'] = {'op': 'add', 'args': [{'var': 'X1'}, {'var': 'X2'}]}
        self.assertTrue(all(1 <= x <= 2 for x in simulate(p)))

    def test_truncated_domain(self):
        p = spec(); p['variables'][0]['domain'] = {'min': 4.9, 'max': 5.1}
        self.assertTrue(all(4.9 <= x <= 5.1 for x in simulate(p)))

    def test_invalid_domain_fails_without_saving(self):
        p = spec('uniform'); p['variables'][0]['domain'] = {'min': 2, 'max': 3}
        with self.assertRaises(Invalid): simulate(p)

    def test_invalid_inputs(self):
        cases = []
        p=spec(); p['variables']*=11; cases.append(p)
        p=spec(); p['variables']*=2; cases.append(p)
        p=spec(); p['samples']=101; cases.append(p)
        p=spec(); p['samples']=True; cases.append(p)
        p=spec(); p['extra']=1; cases.append(p)
        p=spec(); p['variables'][0]['params']['std']=True; cases.append(p)
        p=spec(); p['variables'][0]['params']['std']=0; cases.append(p)
        p=spec(); p['variables'][0]['params']['std']=float('nan'); cases.append(p)
        p=spec(); p['expression']={'var':'X9'}; cases.append(p)
        p=spec(); p['expression']={'const':4}; cases.append(p)
        p=spec(); p['expression']={'op':'__import__','args':[]}; cases.append(p)
        p=spec(); p['expression']={'op':'add','args':[{'var':'X1'}]}; cases.append(p)
        p=spec('categorical'); p['variables'][0]['params']['probabilities']=[.1,.1]; cases.append(p)
        p=spec('generalized_poisson'); p['variables'][0]['params']['theta']=-.1; cases.append(p)
        p=spec(); n={'var':'X1'}
        for _ in range(25): n={'op':'neg','args':[n]}
        p['expression']=n; cases.append(p)
        for i,p in enumerate(cases):
            with self.subTest(i=i), self.assertRaises(Invalid): validate(p)

    def test_non_finite_expression_is_rejected(self):
        for expression in [
            {'op':'div','args':[{'var':'X1'},{'const':0}]},
            {'op':'sqrt','args':[{'op':'neg','args':[{'var':'X1'}]}]},
        ]:
            p=spec('uniform');p['expression']=expression
            with self.assertRaises(Invalid): simulate(p)
        # A bare variable must respect the same output bound as an operation.
        p=spec('lognormal'); p['variables'][0]['params']={'mu':700,'sigma':.1}
        with self.assertRaises(Invalid): simulate(p,seed=42)

    def test_worker_and_hard_timeout(self):
        self.assertEqual(len(run_limited(spec())),100)
        start=time.monotonic()
        with self.assertRaises(TimeoutError): run_limited(spec(),seconds=.3,target=sleeping_worker)
        self.assertLess(time.monotonic()-start,3)
        import multiprocessing
        self.assertFalse(multiprocessing.active_children())

if __name__ == '__main__': unittest.main()
