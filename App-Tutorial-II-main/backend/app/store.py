import secrets
import json
from datetime import datetime, timezone, timedelta
from google.cloud import firestore
from .engine import components, final_results

class LimitReached(Exception): pass
class Conflict(Exception): pass
class Busy(Exception): pass
class DailyLimit(Exception): pass
class LeaseLost(Exception): pass

# Covers admission + 60s child + bounded Firestore write and response cleanup.
# A crashed instance cannot hold the account forever. A stale owner cannot save.
LEASE_SECONDS = 120

def utcnow():
    return datetime.now(timezone.utc)

def active(data, now):
    return data.get('active', {}).get('until', 0) > now.timestamp()

class Store:
    def __init__(self, project):
        self.db = firestore.Client(project=project)

    def ref(self, uid):
        return self.db.collection('montecarlo_users').document(uid)

    def all(self, uid):
        records = (self.ref(uid).get(timeout=15).to_dict() or {}).get('experiments', {})
        return {eid: self.decode(record) for eid, record in records.items()}

    @staticmethod
    def decode(record):
        result = {key: value for key, value in record.items() if key != 'spec_json'}
        result['spec'] = json.loads(record['spec_json'])
        result['dimensions'] = len(components(result['spec']))
        return result

    def usage(self, uid):
        data = self.ref(uid).get(timeout=15).to_dict() or {}
        now = utcnow()
        day = now.date().isoformat()
        used = data.get('daily', {}).get('used', 0) if data.get('daily', {}).get('day') == day else 0
        return {'day_utc': day, 'used': used, 'limit': 25, 'remaining': max(0, 25-used),
                'running': active(data, now),
                'resets_at': datetime.combine(now.date()+timedelta(days=1), datetime.min.time(), timezone.utc).isoformat()}

    def begin(self, uid, payload, request_id, token):
        """Atomic per-account admission, shared across ALL Cloud Run instances.

        Invalid input is rejected before here. Each admitted execution costs one
        daily slot, even when calculation fails/times out. Saved retries are free.
        """
        ref = self.ref(uid)
        @firestore.transactional
        def commit(tx):
            data = ref.get(transaction=tx, timeout=15).to_dict() or {}
            now = utcnow()  # Re-evaluate on transaction retry / UTC midnight.
            if active(data, now): raise Busy()
            experiments = data.get('experiments', {})
            if request_id in experiments:
                previous = self.decode(experiments[request_id])
                if previous['spec'] != payload: raise Conflict()
                return previous
            if len(experiments) >= 10: raise LimitReached()
            day = now.date().isoformat()
            daily = data.get('daily', {})
            used = daily.get('used', 0) if daily.get('day') == day else 0
            if used >= 25: raise DailyLimit()
            data['daily'] = {'day': day, 'used': used + 1}
            data['active'] = {'token': token, 'request_id': request_id,
                              'until': now.timestamp() + LEASE_SECONDS}
            tx.set(ref, data)
            return None
        return commit(self.db.transaction())

    def finish(self, uid, token):
        ref = self.ref(uid)
        @firestore.transactional
        def commit(tx):
            data = ref.get(transaction=tx, timeout=15).to_dict() or {}
            if data.get('active', {}).get('token') == token:
                data.pop('active', None)
                tx.set(ref, data)
        return commit(self.db.transaction())

    def save(self, uid, payload, results, request_id, token):
        ref = self.ref(uid)
        record = {'id': request_id, 'title': payload['title'].strip(),
                  'created_at': utcnow().isoformat(timespec='milliseconds'),
                  'color': f'#{secrets.randbelow(0x777777) + 0x222222:06x}',
                  'dimensions': len(components(payload)),
                  # JSON text avoids Firestore's map/array nesting depth limit.
                  'spec_json': json.dumps(payload, ensure_ascii=False, allow_nan=False, separators=(',', ':')),
                  'results': final_results(payload, results)}
        @firestore.transactional
        def commit(tx):
            data = ref.get(transaction=tx, timeout=15).to_dict() or {}
            lease = data.get('active', {})
            if lease.get('token') != token or lease.get('request_id') != request_id or not active(data, utcnow()):
                raise LeaseLost()
            experiments = data.get('experiments', {})
            if len(experiments) >= 10: raise LimitReached()
            experiments[request_id] = record
            data['experiments'] = experiments
            # Release and save atomically; finish() is an idempotent fallback.
            data.pop('active', None)
            tx.set(ref, data)
            return self.decode(record)
        return commit(self.db.transaction())

    def delete(self, uid, eid):
        ref = self.ref(uid)
        @firestore.transactional
        def commit(tx):
            data = ref.get(transaction=tx, timeout=15).to_dict() or {}
            if active(data, utcnow()): raise Busy()
            experiments = data.get('experiments', {})
            if eid not in experiments: return False
            del experiments[eid]
            data['experiments'] = experiments
            # Keep daily counters: deletion never refunds daily quota.
            tx.set(ref, data)
            return True
        return commit(self.db.transaction())

