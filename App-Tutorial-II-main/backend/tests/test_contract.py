"""Contract, ingress and final-result regression tests; no real credentials."""
import copy
import json
import math
from pathlib import Path
import re
import unittest
from unittest.mock import patch
import numpy as np
from app.engine import (Invalid, PARAMETER_RANGES, final_results, references,
                        simulate, validate, validate_variable)
from app.runner import run_limited
from app import main
from test_engine import spec, PARAMETERS, sum_ast
import test_api


class ContractTests(unittest.TestCase):
    def test_all_parameter_boundaries_and_non_numeric_values(self):
        for distribution, fields in PARAMETER_RANGES.items():
            if distribution == 'uniform': continue
            for field, (lower, upper) in fields.items():
                for value in (lower, upper):
                    v=spec(distribution)['variables'][0];v['params'][field]=value
                    with self.subTest(distribution=distribution,field=field,value=value):validate_variable(v)
                for value in (math.nextafter(lower,-math.inf),math.nextafter(upper,math.inf),True,'1',None,[],float('nan'),float('inf'),10**400):
                    v=spec(distribution)['variables'][0];v['params'][field]=value
                    with self.subTest(distribution=distribution,field=field,value=str(value)[:20]),self.assertRaises(Invalid):validate_variable(v)
        for low,high in ((0,10),(0,.001),(9.999,10)):validate_variable({'name':'X1','distribution':'uniform','params':{'low':low,'high':high}})
        for low,high in ((-1,10),(0,11),(5,5),(6,5),(0,0)):
            with self.assertRaises(Invalid):validate_variable({'name':'X1','distribution':'uniform','params':{'low':low,'high':high}})

    def test_mobile_backend_parameter_ranges_are_identical(self):
        source=(Path(__file__).resolve().parents[2]/'mobile/src/distributions.ts').read_text(encoding='utf-8')
        table=re.search(r'export const PARAMETER_RANGES:[^=]+ = (\{.*?\});',source,re.S)
        self.assertIsNotNone(table)
        self.assertEqual(json.loads(table.group(1)),PARAMETER_RANGES)

    def test_log_location_scale_matches_numpy_and_legacy_key_is_rejected(self):
        p=spec('lognormal');p['variables'][0]['params']={'mu':.6,'sigma':.35}
        from decimal import Decimal,ROUND_DOWN
        raw=np.random.default_rng(42).lognormal(mean=.6,sigma=.35,size=100)
        expected=[float(Decimal(str(x)).quantize(Decimal('.001'),rounding=ROUND_DOWN)) for x in raw]
        self.assertEqual(simulate(p,seed=42),expected)
        p['variables'][0]['params']={'mean':0,'sigma':.25}
        with self.assertRaises(Invalid):validate(p)

    def test_categorical_ten_options_and_all_constraints(self):
        p=spec('categorical');p['variables'][0]['params']={'values':list(range(10)),'probabilities':[.1]*10}
        self.assertEqual(len(simulate(p)),100)
        for values,probabilities in ((list(range(11)),[1/11]*11),([],[]),([1,1],[.5,.5]),([-1,1],[.5,.5]),([1,11],[.5,.5]),([1,2],[.1,.1]),([1,2],[-.1,1.1]),([True],[1]),([1],[True]),([1],[1,0])):
            p['variables'][0]['params']={'values':values,'probabilities':probabilities}
            with self.subTest(values=values),self.assertRaises(Invalid):validate(p)

    def test_references_are_distinct_shared_and_all_defined_are_used(self):
        p=spec('uniform');p['expression']=sum_ast(['X1']*15)
        self.assertEqual(references(p['expression']),{'X1'});self.assertEqual(len(simulate(p)),100)
        p.pop('expression');p.update(version=2,expressions=[sum_ast([f'X{i}' for i in range(1,6)])]*3)
        p['variables']=[{'name':f'X{i}','distribution':'uniform','params':{'low':0,'high':1}} for i in range(1,6)]
        out=np.array(simulate(p,seed=42)).reshape(100,3)
        np.testing.assert_array_equal(out[:,0],out[:,1]);np.testing.assert_array_equal(out[:,0],out[:,2])
        p['variables'].append({'name':'X6','distribution':'uniform','params':{'low':0,'high':1}})
        with self.assertRaisesRegex(Invalid,'utilizarse'):validate(p)
        p['expressions'][0]=sum_ast([f'X{i}' for i in range(1,7)])
        with self.assertRaisesRegex(Invalid,'máximo 5'):validate(p)

    def test_final_components_truncate_without_truncating_intermediate_variables(self):
        p=spec('categorical');p['variables'][0]['params']={'values':[1.23456],'probabilities':[1]}
        p.pop('expression');p.update(version=2,expressions=[{'var':'X1'},{'op':'pow','args':[{'var':'X1'},{'const':2}]}])
        out=np.array(simulate(p)).reshape(100,2)
        np.testing.assert_array_equal(out[:,0],np.full(100,1.234))
        np.testing.assert_array_equal(out[:,1],np.full(100,1.524))
        values=[1.2349,-1.2349,1.001,-1.001,.0009,-.0009,9.9999,1e100]+[0.]*92
        truncated=final_results(spec(),values)
        self.assertEqual(truncated[:8],[1.234,-1.234,1.001,-1.001,0.,0.,9.999,1e100])
        self.assertEqual(final_results(spec(),truncated),truncated)
        self.assertEqual(math.copysign(1,truncated[5]),1)

    def test_final_result_shape_values_and_worker_prevalidation(self):
        for result in ([],[1.]*99,[1.]*101,[[1.]]*100,[True]*100,[float('nan')]*100,[float('inf')]*100,[1e101]*100,['1.234']*100):
            with self.subTest(result=str(result)[:25]),self.assertRaises(Invalid):final_results(spec(),result)
        p=spec();p['variables'][0]['params']['std']=1
        with patch('app.runner.mp.get_context') as context,self.assertRaises(Invalid):run_limited(p)
        context.assert_not_called()

    def test_no_forced_zero_ten_domain_or_component_clipping(self):
        p=spec('uniform');p['variables'][0]['params']={'low':9,'high':10}
        p['expression']={'op':'mul','args':[{'var':'X1'},{'const':2}]}
        self.assertTrue(all(18<=x<=20 for x in simulate(p)))
        p=spec();p['variables'][0]['domain']={'min':5,'max':5.5}
        self.assertTrue(all(5<=x<=5.5 for x in simulate(p)))


class IngressTests(unittest.TestCase):
    setUp=test_api.APITests.setUp
    tearDown=test_api.APITests.tearDown
    create=test_api.APITests.create

    def assert_never_started(self):
        self.mock_runner.assert_not_called()
        self.assertEqual(self.store.usage('alice')['used'],0)
        self.assertEqual(self.store.all('alice'),{})

    def test_invalid_wire_formats_never_start_or_charge(self):
        valid=json.dumps(spec()).encode()
        cases=[({},valid,415),({'Content-Type':'text/plain'},valid,415),
               ({'Content-Type':'application/json; charset=utf-16'},valid,415),
               ({'Content-Type':'application/json','Content-Encoding':'gzip'},valid,415),
               ({'Content-Type':'application/json'},b'\xff',422),
               ({'Content-Type':'application/json'},'{}'.encode('utf-16'),422),
               ({'Content-Type':'application/json'},b'{"x":NaN}',422),
               ({'Content-Type':'application/json'},b'{"x":Infinity}',422),
               ({'Content-Type':'application/json'},b'{"x":1,"x":2}',422),
               ({'Content-Type':'application/json'},b'[]',422),
               ({'Content-Type':'application/json'},b'null',422),
               ({'Content-Type':'application/json'},b'{}{}',422),
               ({'Content-Type':'application/json'},b' '*32769,413)]
        for headers,body,status in cases:
            with self.subTest(headers=headers,body=body[:20]):
                response=self.client.post('/v1/experiments',content=body,headers=headers)
                self.assertEqual(response.status_code,status,response.text)
        self.assert_never_started()

    def test_duplicate_nested_fields_and_large_chunked_body(self):
        text=json.dumps(spec()).replace('"std": 0.5','"std": 0.5, "std": 0.6')
        r=self.client.post('/v1/experiments',content=text,headers={'Content-Type':'application/json'})
        self.assertEqual(r.status_code,422)
        r=self.client.post('/v1/experiments',content=iter([b' '*16000,b' '*17000]),headers={'Content-Type':'application/json'})
        self.assertEqual(r.status_code,413)
        self.assert_never_started()

    def test_content_length_and_duplicate_id_headers(self):
        body=json.dumps(spec()).encode();headers={'Content-Type':'application/json','Content-Length':str(len(body)+1)}
        self.assertEqual(self.client.post('/v1/experiments',content=body,headers=headers).status_code,400)
        headers['Content-Length']='-1'
        self.assertEqual(self.client.post('/v1/experiments',content=body,headers=headers).status_code,400)
        headers=[('Content-Type','application/json'),('Idempotency-Key','00000000-0000-4000-8000-000000000000'),('Idempotency-Key','00000001-0000-4000-8000-000000000000')]
        self.assertEqual(self.client.post('/v1/experiments',content=body,headers=headers).status_code,422)
        self.assert_never_started()

    def test_ranges_and_schemas_reject_before_admission(self):
        cases=[]
        for distribution,fields in PARAMETER_RANGES.items():
            for field,(lower,upper) in fields.items():
                for value in (math.nextafter(lower,-math.inf),math.nextafter(upper,math.inf)):
                    p=spec(distribution);p['variables'][0]['params'][field]=value;cases.append(p)
        for value in (None,[],True,2.0,'2'):
            p=spec();p['version']=value;cases.append(p)
        p=spec();p['variables'][0]['params']['extra']=1;cases.append(p)
        p=spec();p['variables'][0]['base_results']=[1]*100;cases.append(p)
        p=spec();p['results']=[1]*100;cases.append(p)
        p=spec();p['expression']={'op':'eval','args':[{'var':'X1'}]};cases.append(p)
        p=spec();p['samples']=101;cases.append(p)
        p=spec();p.pop('expression');p.update(version=2,expressions=[sum_ast([f'X{i}' for i in range(1,7)]),{'var':'X1'}]);p['variables']=[{'name':f'X{i}','distribution':'uniform','params':{'low':0,'high':1}} for i in range(1,7)];cases.append(p)
        for p in cases:
            with self.subTest(payload=p):self.assertEqual(self.create(0,p).status_code,422)
        self.assert_never_started()

    def test_truncated_components_only_are_persisted_and_retry_is_identical(self):
        p=spec('categorical');p['variables'][0]['params']={'values':[1.23456],'probabilities':[1]}
        p.pop('expression');p.update(version=2,expressions=[{'var':'X1'},{'op':'pow','args':[{'var':'X1'},{'const':2}]}])
        with patch.object(main,'run_limited',side_effect=lambda payload,seconds:simulate(payload)) as runner:
            a=self.create(0,p);b=self.create(0,p)
        self.assertEqual(a.status_code,201,a.text);self.assertEqual(a.json(),b.json());self.assertEqual(runner.call_count,1)
        self.assertEqual(a.json()['results'],[1.234,1.524]*100)
        record=self.store.ref('alice').data['experiments'][a.json()['id']]
        self.assertEqual(set(record),{'id','title','created_at','color','dimensions','spec_json','results'})
        self.assertEqual(len(record['results']),200)
        self.assertNotIn('results',json.loads(record['spec_json'])['variables'][0])

    def test_real_worker_fifteen_variable_api_roundtrip(self):
        p=spec('uniform');p.pop('expression')
        p.update(version=2,expressions=[sum_ast([f'X{i}' for i in range(d*5+1,d*5+6)]) for d in range(3)])
        p['variables']=[{'name':f'X{i}','distribution':'uniform','params':{'low':0,'high':10}} for i in range(1,16)]
        with patch.object(main,'run_limited',side_effect=run_limited) as runner:
            response=self.create(0,p);retry=self.create(0,p)
        self.assertEqual(response.status_code,201,response.text)
        self.assertEqual(response.json(),retry.json());self.assertEqual(runner.call_count,1)
        self.assertEqual(len(response.json()['results']),300)
        self.assertEqual(self.store.usage('alice')['used'],1)
        from decimal import Decimal
        for value in response.json()['results']:
            self.assertGreaterEqual(Decimal(str(value)).as_tuple().exponent,-3)

    def test_bad_worker_output_is_not_persisted_and_releases_lease(self):
        with patch.object(main,'run_limited',return_value=[float('nan')]*100):r=self.create(0)
        self.assertEqual(r.status_code,422)
        self.assertFalse(self.store.all('alice'));self.assertFalse(self.store.usage('alice')['running'])

    def test_auth_verifies_token_revocation_and_provider_before_running(self):
        main.app.dependency_overrides.clear()
        claims={'uid':'alice','firebase':{'sign_in_provider':'google.com'}}
        with patch.object(main.firebase_admin,'_apps',{'test':object()}),patch.object(main.auth,'verify_id_token',return_value=claims) as verify:
            response=self.client.get('/v1/usage',headers={'Authorization':'Bearer valid-test-token'})
            self.assertEqual(response.status_code,200);verify.assert_called_once_with('valid-test-token',check_revoked=True)
        for claims in ({'uid':'alice','firebase':{'sign_in_provider':'password'}},{'firebase':{'sign_in_provider':'google.com'}}):
            with patch.object(main.firebase_admin,'_apps',{'test':object()}),patch.object(main.auth,'verify_id_token',return_value=claims):
                r=self.client.post('/v1/experiments',json=spec(),headers={'Authorization':'Bearer invalid-test-token'})
                self.assertEqual(r.status_code,401)
        with patch.object(main.firebase_admin,'_apps',{'test':object()}),patch.object(main.auth,'verify_id_token',side_effect=ValueError('revoked')):
            self.assertEqual(self.client.get('/v1/usage',headers={'Authorization':'Bearer revoked'}).status_code,401)
        self.assert_never_started()


if __name__=='__main__':unittest.main()
