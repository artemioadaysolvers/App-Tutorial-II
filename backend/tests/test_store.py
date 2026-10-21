import copy
import json
import threading
import unittest
import uuid
from datetime import datetime, timezone, timedelta
from unittest.mock import patch
from app.store import Store, LimitReached, Conflict, Busy, DailyLimit, LeaseLost, LEASE_SECONDS
from app.engine import validate
from test_engine import spec

class Snapshot:
    def __init__(self, data): self.data = data
    def to_dict(self): return copy.deepcopy(self.data)
class Reference:
    def __init__(self): self.data = None
    def get(self, **kwargs): return Snapshot(self.data)
class Transaction:
    def set(self, ref, data): ref.data = copy.deepcopy(data)
class Database:
    def transaction(self): return Transaction()
class MemoryStore(Store):
    def __init__(self): self.db=Database();self.refs={}
    def ref(self,uid): return self.refs.setdefault(uid,Reference())

# Serialized fake transport runs the actual Store logic; emulator integration
# separately exercises the real SDK's cross-client transaction behavior.
transport_lock=threading.RLock()
def transactional(fn):
    def wrapped(*args,**kwargs):
        with transport_lock: return fn(*args,**kwargs)
    return wrapped

class StoreTests(unittest.TestCase):
    def setUp(self):
        self.store=MemoryStore();self.ref=self.store.ref('alice')
        self.decorator=patch('app.store.firestore.transactional',side_effect=transactional);self.decorator.start()
    def tearDown(self): self.decorator.stop()
    def save(self,eid=None,payload=None,results=None):
        eid=eid or str(uuid.uuid4());payload=payload or spec();token=str(uuid.uuid4())
        previous=self.store.begin('alice',payload,eid,token)
        if previous is not None:return previous
        return self.store.save('alice',payload,results or [1.]*100,eid,token)
    def test_deep_ast_and_vector_flat_storage(self):
        payload=spec();ast={'var':'X1'}
        for _ in range(19):ast={'op':'neg','args':[ast]}
        payload.pop('expression');payload.update(version=2,expressions=[ast,{'var':'X1'},{'var':'X1'}]);validate(payload)
        record=self.save(payload=payload,results=[2.]*300)
        self.assertRegex(record['created_at'],r'T\d{2}:\d{2}:\d{2}\.\d{3}\+00:00$')
        stored=self.ref.data['experiments'][record['id']]
        self.assertNotIn('spec',stored);self.assertIsInstance(stored['spec_json'],str)
        self.assertEqual(json.loads(stored['spec_json']),payload)
        self.assertEqual(record['dimensions'],3);self.assertEqual(len(stored['results']),300)
        self.assertTrue(all(isinstance(x,float) for x in stored['results']))
        self.assertEqual(self.store.all('alice')[record['id']]['spec'],payload)
        def depth(obj):
            if isinstance(obj,dict):return 1+max((depth(x) for x in obj.values()),default=0)
            if isinstance(obj,list):return 1+max((depth(x) for x in obj),default=0)
            return 0
        self.assertLessEqual(depth(self.ref.data),5)
    def test_saved_quota_retry_conflict_delete_preserves_daily(self):
        ids=[str(uuid.uuid4()) for _ in range(11)]
        for eid in ids[:10]:self.save(eid)
        with self.assertRaises(LimitReached):self.save(ids[10])
        self.assertEqual(self.save(ids[0],results=[2.]*100)['results'],[1.]*100)
        changed=spec();changed['title']='Otro'
        with self.assertRaises(Conflict):self.save(ids[0],payload=changed)
        self.assertEqual(self.store.usage('alice')['used'],10)
        self.assertTrue(self.store.delete('alice',ids[0]));self.assertFalse(self.store.delete('alice',ids[0]))
        self.save(ids[10]);self.assertEqual(len(self.store.all('alice')),10)
        self.assertEqual(self.store.usage('alice')['used'],11)
    def test_daily_25_attempts_failure_and_midnight_utc(self):
        now=datetime(2026,10,20,23,59,tzinfo=timezone.utc)
        with patch('app.store.utcnow',return_value=now):
            for i in range(25):
                token=str(i);self.store.begin('alice',spec(),str(uuid.uuid4()),token)
                self.store.finish('alice',token) # Failure consumes the slot.
            self.assertEqual(self.store.usage('alice')['remaining'],0)
            with self.assertRaises(DailyLimit):self.store.begin('alice',spec(),str(uuid.uuid4()),'blocked')
            self.assertEqual(self.store.usage('bob')['remaining'],25)
        with patch('app.store.utcnow',return_value=now+timedelta(minutes=2)):
            self.assertEqual(self.store.usage('alice')['remaining'],25)
            self.store.begin('alice',spec(),str(uuid.uuid4()),'nextday')
            self.assertEqual(self.store.usage('alice')['used'],1)
    def test_active_lock_failed_release_and_stale_owner_fencing(self):
        now=datetime(2026,10,20,tzinfo=timezone.utc);eid=str(uuid.uuid4())
        with patch('app.store.utcnow',return_value=now):
            self.store.begin('alice',spec(),eid,'first')
            with self.assertRaises(Busy):self.store.begin('alice',spec(),str(uuid.uuid4()),'second')
            with self.assertRaises(Busy):self.store.delete('alice',eid)
            self.store.finish('alice','wrong');self.assertTrue(self.store.usage('alice')['running'])
            self.assertEqual(self.store.usage('alice')['used'],1)
        with patch('app.store.utcnow',return_value=now+timedelta(seconds=LEASE_SECONDS+1)):
            self.store.begin('alice',spec(),eid,'second')
            with self.assertRaises(LeaseLost):self.store.save('alice',spec(),[1.]*100,eid,'first')
            self.store.finish('alice','first');self.assertTrue(self.store.usage('alice')['running'])
            self.store.save('alice',spec(),[1.]*100,eid,'second')
            self.assertFalse(self.store.usage('alice')['running'])
    def test_simultaneous_admission_one_slot_only(self):
        import concurrent.futures
        def admit(i):
            try:self.store.begin('alice',spec(),str(uuid.uuid4()),str(i));return True
            except Busy:return False
        with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
            self.assertEqual(sum(pool.map(admit,range(16))),1)
        self.assertEqual(self.store.usage('alice')['used'],1)
