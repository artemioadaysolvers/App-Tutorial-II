"""Optional integration: real Firestore SDK, local emulator only."""
import concurrent.futures
import os
import unittest
import uuid
from app.store import Store, Busy, DailyLimit
from test_engine import spec

@unittest.skipUnless(os.environ.get('FIRESTORE_EMULATOR_HOST'), 'Requiere emulador Firestore local')
class FirestoreIntegration(unittest.TestCase):
    def test_cross_instance_admission_daily_quota_and_deletion(self):
        if not os.environ['FIRESTORE_EMULATOR_HOST'].startswith(('127.0.0.1:', 'localhost:')):
            self.fail('Usa un emulador local, no una base real.')
        project='montecarlo-local-tests';uid='test-'+str(uuid.uuid4());first=Store(project)
        def admit(i):
            token=str(uuid.uuid4());eid=str(uuid.uuid4())
            try:
                Store(project).begin(uid,spec(),eid,token)
                return (eid,token)
            except Busy:return None
        try:
            with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
                accepted=[v for v in pool.map(admit,range(12)) if v is not None]
            self.assertEqual(len(accepted),1);self.assertEqual(first.usage(uid)['used'],1)
            eid,token=accepted[0]
            record=first.save(uid,spec(),[1.]*100,eid,token)
            self.assertEqual(first.begin(uid,spec(),eid,'retry'),record)
            first.delete(uid,eid)
            for _ in range(24):
                token=str(uuid.uuid4());first.begin(uid,spec(),str(uuid.uuid4()),token);first.finish(uid,token)
            with self.assertRaises(DailyLimit):first.begin(uid,spec(),str(uuid.uuid4()),'over-quota')
            self.assertEqual(first.usage(uid)['used'],25)
        finally:first.ref(uid).delete()
