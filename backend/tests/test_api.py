import json
import unittest
from unittest.mock import patch
from fastapi.testclient import TestClient
from app import main
from test_engine import spec
from test_store import MemoryStore, transactional

class APITests(unittest.TestCase):
    def setUp(self):
        self.store=MemoryStore();main._store=self.store
        self.tx=patch('app.store.firestore.transactional',side_effect=transactional);self.tx.start()
        main.app.dependency_overrides[main.user]=lambda:'alice';self.client=TestClient(main.app)
        self.runner=patch.object(main,'run_limited',return_value=[1.]*100);self.mock_runner=self.runner.start()
    def tearDown(self):
        self.runner.stop();self.tx.stop();main.app.dependency_overrides.clear();main._store=None
    def create(self,i,payload=None):
        return self.client.post('/v1/experiments',json=payload or spec(),headers={'Idempotency-Key':f'{i:08x}-0000-4000-8000-000000000000'})
    def test_quota_idempotency_delete_and_isolation(self):
        for i in range(10):self.assertEqual(self.create(i).status_code,201)
        self.assertEqual(self.create(0).status_code,201);self.assertEqual(self.create(10).status_code,409)
        records=self.client.get('/v1/experiments').json();self.assertEqual(len(records),10);self.assertNotIn('results',records[0])
        eid=records[0]['id'];self.assertEqual(len(self.client.get('/v1/experiments/'+eid).json()['results']),100)
        main.app.dependency_overrides[main.user]=lambda:'bob'
        self.assertEqual(self.client.get('/v1/experiments').json(),[])
        self.assertEqual(self.client.get('/v1/experiments/'+eid).status_code,404)
        self.assertEqual(self.client.delete('/v1/experiments/'+eid).status_code,404)
        main.app.dependency_overrides[main.user]=lambda:'alice'
        self.assertEqual(self.client.delete('/v1/experiments/'+eid).status_code,204)
        self.assertEqual(self.create(10).status_code,201)
        self.assertEqual(self.client.get('/v1/usage').json()['used'],11)
    def test_rejects_payload_without_charging(self):
        for text in ['{}','{"version":1,"version":1}',json.dumps(spec()).replace('"std": 1','"std": NaN')]:
            self.assertEqual(self.client.post('/v1/experiments',content=text).status_code,422)
        self.assertEqual(self.client.post('/v1/experiments',content=' '*33000).status_code,413)
        self.assertEqual(self.store.usage('alice')['used'],0)
        p=spec();p['variables']=[{'name':f'X{i}','distribution':'normal','params':{'mean':0,'std':1}} for i in range(1,5)]
        self.assertEqual(self.create(0,p).status_code,422)
        self.assertEqual(self.store.usage('alice')['used'],0)
    def test_timeout_no_persistence_releases_lock_charges_attempt(self):
        with patch.object(main,'run_limited',side_effect=TimeoutError('60 segundos')):
            self.assertEqual(self.create(0).status_code,408)
        self.assertFalse(self.store.all('alice'));self.assertFalse(self.store.usage('alice')['running'])
        self.assertEqual(self.store.usage('alice')['used'],1)
    def test_busy_and_unauthenticated(self):
        main.gate.acquire()
        try:self.assertEqual(self.create(0).status_code,429)
        finally:main.gate.release()
        self.store.begin('alice',spec(),'already-active','other-instance')
        self.assertEqual(self.create(0).status_code,429);self.mock_runner.assert_not_called()
        main.app.dependency_overrides.clear()
        for route in ['/v1/experiments','/v1/usage']:self.assertEqual(self.client.get(route).status_code,401)
    def test_daily_limit_enforced_even_after_deletion(self):
        for i in range(25):
            response=self.create(i);self.assertEqual(response.status_code,201)
            self.assertEqual(self.client.delete('/v1/experiments/'+response.json()['id']).status_code,204)
        self.assertEqual(self.create(25).status_code,429)
        self.assertEqual(self.mock_runner.call_count,25)
        self.assertEqual(self.client.get('/v1/usage').json()['remaining'],0)
    def test_vector_roundtrip_and_saved_retry_does_not_run_or_charge(self):
        p=spec();p.pop('expression');p.update(version=2,expressions=[{'var':'X1'}]*3)
        with patch.object(main,'run_limited',return_value=list(range(300))) as runner:
            a=self.create(0,p);b=self.create(0,p)
            self.assertEqual(a.status_code,201);self.assertEqual(a.json(),b.json())
            self.assertEqual(a.json()['dimensions'],3);self.assertEqual(len(a.json()['results']),300)
            self.assertEqual(runner.call_count,1);self.assertEqual(self.store.usage('alice')['used'],1)
    def test_no_new_attempt_while_worker_is_running(self):
        # Simulates a second Cloud Run instance with its own local gate. Both
        # handlers still share the Firestore admission transaction by UID.
        def running(payload,seconds):
            self.assertTrue(self.store.usage('alice')['running'])
            from app.store import Busy
            with self.assertRaises(Busy):self.store.begin('alice',spec(),'other','other-token')
            return [1.]*100
        with patch.object(main,'run_limited',side_effect=running):self.assertEqual(self.create(0).status_code,201)
        self.assertFalse(self.store.usage('alice')['running'])

if __name__ == '__main__':unittest.main()
