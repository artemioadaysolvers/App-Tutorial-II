"""A killed child process enforces the wall clock bound, not a thread timeout."""
import multiprocessing as mp
import time

def worker(conn, payload):
    try:
        from .engine import simulate
        conn.send({'results': simulate(payload)})
    except Exception as exc:
        conn.send({'error': str(exc)[:500]})
    finally:
        conn.close()

def run_limited(payload, seconds=60, target=worker):
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
        if 'error' in response:
            raise ValueError(response['error'])
        return response['results']
    finally:
        if process.is_alive(): process.terminate()
        process.join(timeout=1)
        if process.is_alive():
            process.kill()
            process.join()
        receiver.close()
