import json
import logging
import os
import re
import threading
import secrets
import time
import firebase_admin
from firebase_admin import auth
from fastapi import FastAPI, Request, HTTPException, Depends
from starlette.concurrency import run_in_threadpool
from .engine import validate, Invalid
from .runner import run_limited
from .store import Store, LimitReached, Conflict, Busy, DailyLimit, LeaseLost

app = FastAPI(title='Monte Carlo Lab', version='2.0.0')
project = os.environ.get('GOOGLE_CLOUD_PROJECT', '')
gate = threading.BoundedSemaphore(1)
_store = None

def store():
    global _store
    if _store is None: _store = Store(project)
    return _store

def user(request: Request):
    values = request.headers.getlist('authorization')
    value = values[0] if len(values) == 1 else ''
    if not value.startswith('Bearer ') or len(value) > 10000:
        raise HTTPException(401, 'Inicia sesión con Google.')
    try:
        if not firebase_admin._apps:
            firebase_admin.initialize_app(options={'projectId': project})
        token = auth.verify_id_token(value[7:], check_revoked=True)
        if token.get('firebase', {}).get('sign_in_provider') != 'google.com':
            raise ValueError('Google required')
        return token['uid']
    except Exception:
        raise HTTPException(401, 'Sesión inválida o vencida. Vuelve a iniciar sesión.')

def identifier(eid):
    if not re.fullmatch(r'[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}', eid):
        raise HTTPException(422, 'Identificador inválido.')

@app.exception_handler(Exception)
async def unexpected(request, exc):
    from fastapi.responses import JSONResponse
    logging.exception('Request failed')
    return JSONResponse(status_code=503, content={'detail': 'Servicio no disponible. Inténtalo de nuevo.'})

@app.get('/health')
def health():
    return {'status': 'ok'}

@app.get('/v1/experiments')
def listing(uid=Depends(user)):
    records = store().all(uid).values()
    return sorted([{k: v for k, v in r.items() if k not in ('results', 'spec')} for r in records],
                  key=lambda x: x['created_at'], reverse=True)

@app.get('/v1/usage')
def usage(uid=Depends(user)):
    return store().usage(uid)

@app.get('/v1/experiments/{eid}')
def detail(eid: str, uid=Depends(user)):
    identifier(eid)
    result = store().all(uid).get(eid)
    if result is None: raise HTTPException(404, 'Experimento no encontrado.')
    return result

@app.delete('/v1/experiments/{eid}', status_code=204)
def delete(eid: str, uid=Depends(user)):
    identifier(eid)
    try:
        if not store().delete(uid, eid): raise HTTPException(404, 'Experimento no encontrado.')
    except Busy: raise HTTPException(429, 'Tu cuenta tiene una simulación en curso. Espera antes de borrar.')

@app.post('/v1/experiments', status_code=201)
async def create(request: Request, uid=Depends(user)):
    # Strict wire format is checked before validation, admission or computation.
    content_types = request.headers.getlist('content-type')
    if len(content_types) != 1:
        raise HTTPException(415, 'Envía un único Content-Type: application/json.')
    parts = [p.strip().lower() for p in content_types[0].split(';')]
    if parts[0] != 'application/json' or len(parts) > 2 or (len(parts) == 2 and parts[1] not in ('charset=utf-8', 'charset="utf-8"')):
        raise HTTPException(415, 'Se requiere application/json codificado en UTF-8.')
    encodings = request.headers.getlist('content-encoding')
    if len(encodings) > 1 or (encodings and encodings[0].strip().lower() != 'identity'):
        raise HTTPException(415, 'No se admiten cuerpos comprimidos.')
    lengths = request.headers.getlist('content-length')
    if len(lengths) > 1 or (lengths and not re.fullmatch(r'[0-9]{1,10}', lengths[0])):
        raise HTTPException(400, 'Content-Length inválido.')
    declared = int(lengths[0]) if lengths else None
    if declared is not None and declared > 32768:
        raise HTTPException(413, 'JSON demasiado grande (32 KiB).')
    chunks = bytearray()
    async for chunk in request.stream():
        if len(chunks) + len(chunk) > 32768:
            raise HTTPException(413, 'JSON demasiado grande (32 KiB).')
        chunks.extend(chunk)
    if declared is not None and declared != len(chunks):
        raise HTTPException(400, 'El tamaño del cuerpo no coincide con Content-Length.')
    def no_duplicates(pairs):
        out = {}
        for key, value in pairs:
            if key in out: raise Invalid('Claves JSON duplicadas.')
            out[key] = value
        return out
    try:
        payload = json.loads(chunks.decode('utf-8'), object_pairs_hook=no_duplicates,
                             parse_constant=lambda _: (_ for _ in ()).throw(Invalid('Número JSON inválido.')))
        validate(payload)
    except (ValueError, TypeError, RecursionError, OverflowError):
        raise HTTPException(422, 'Formato inválido. Revisa variables, parámetros, dominio y expresión.')
    request_ids = request.headers.getlist('idempotency-key')
    rid = request_ids[0] if len(request_ids) == 1 else ''
    identifier(rid)
    if not gate.acquire(blocking=False): raise HTTPException(429, 'Hay una simulación en curso. Reintenta.')
    token = secrets.token_hex(24)
    admitted = False
    admission_start = time.monotonic()
    try:
        try:
            previous = await run_in_threadpool(store().begin, uid, payload, rid, token)
        except Busy: raise HTTPException(429, 'Tu cuenta ya tiene una simulación en curso. Espera a que termine.')
        except DailyLimit: raise HTTPException(429, 'Alcanzaste 25 escenarios hoy. El cupo se reinicia a las 00:00 UTC.')
        except LimitReached: raise HTTPException(409, 'Ya tienes 10 experimentos. Borra uno para continuar.')
        except Conflict: raise HTTPException(409, 'La clave ya pertenece a otra solicitud.')
        if previous is not None: return previous
        admitted = True
        try:
            # Even a delayed admission response cannot start a child beyond its
            # distributed lease. Leave 15s for persistence, never exceed 60s.
            seconds = min(60, 120 - (time.monotonic() - admission_start) - 15)
            if seconds <= 0: raise TimeoutError('La reserva venció antes del cálculo. Reintenta.')
            results = await run_in_threadpool(run_limited, payload, seconds=seconds)
        except TimeoutError as exc: raise HTTPException(408, str(exc))
        except ValueError as exc: raise HTTPException(422, str(exc))
        try:
            return await run_in_threadpool(store().save, uid, payload, results, rid, token)
        except LimitReached: raise HTTPException(409, 'Ya tienes 10 experimentos. Borra uno.')
        except Conflict: raise HTTPException(409, 'La clave ya pertenece a otra solicitud.')
        except LeaseLost: raise HTTPException(409, 'La reserva venció. Consulta la tabla antes de reintentar.')
        except Invalid as exc: raise HTTPException(422, str(exc))
    finally:
        try:
            if admitted: await run_in_threadpool(store().finish, uid, token)
        except Exception:
            logging.exception('Reservation cleanup failed; lease will expire')
        finally:
            gate.release()
