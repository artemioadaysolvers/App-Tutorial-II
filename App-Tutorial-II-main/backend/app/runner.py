"""A killed child process enforces the wall clock bound, not a thread timeout."""
import multiprocessing as mp
import time
from .engine import validate, final_results

def worker(conn, payload):
    try:
        from .engine import simulate
        conn.send({'results': simulate(payload)})
    except Exception as exc:
        conn.send({'error': str(exc)[:500]})
    finally:
        conn.close()

def run_limited(payload, seconds=60, target=worker):
    validate(payload)  # No process starts for an invalid specification.
    context = mp.get_context('spawn')
    receiver, sender = context.Pipe(duplex=False)
    process = context.Process(target=target, args=(sender, payload), daemon=True)
    start = time.monotonic()
    process.start()
    sender.close()
    try:
        if not receiver.poll(max(0, seconds - (time.monotonic() - start))):
            raise TimeoutError('Se alcanzó el máximo de 60 segundos de simulación.')
        try:
            response = receiver.recv()
        except EOFError as exc:
            raise ValueError('El proceso de simulación terminó inesperadamente.') from exc
        if type(response) is not dict:
            raise ValueError('Respuesta inválida del proceso de simulación.')
        if set(response) == {'error'} and type(response['error']) is str:
            raise ValueError(response['error'])
        if set(response) != {'results'}:
            raise ValueError('Respuesta inválida del proceso de simulación.')
        return final_results(payload, response['results'])
    finally:
        if process.is_alive(): process.terminate()
        process.join(timeout=1)
        if process.is_alive():
            process.kill()
            process.join()
        receiver.close()
