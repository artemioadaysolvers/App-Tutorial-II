"""Only the calculation deadline changes; HTTP remains at its original value."""
import ast
import inspect
import multiprocessing
from pathlib import Path
import time
import unittest
from unittest.mock import patch, Mock
from app.runner import run_limited, SIMULATION_TIMEOUT_SECONDS
from test_engine import spec


def infinite_worker(conn,payload):
    while True:
        pass


class TimeoutTests(unittest.TestCase):
    def test_default_and_api_share_thirty_second_limit(self):
        self.assertEqual(SIMULATION_TIMEOUT_SECONDS,30)
        self.assertEqual(inspect.signature(run_limited).parameters['seconds'].default,30)
        source=(Path(__file__).resolve().parents[1]/'app/main.py').read_text(encoding='utf-8')
        tree=ast.parse(source)
        assignments=[n for n in ast.walk(tree) if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='seconds' for t in n.targets)]
        self.assertEqual(len(assignments),1)
        self.assertEqual(assignments[0].value.args[0].id,'SIMULATION_TIMEOUT_SECONDS')

    def test_explicit_caller_cannot_request_an_hour(self):
        with patch('app.runner.mp.get_context') as context,patch('app.runner.time.monotonic',side_effect=[100,100.125]):
            receiver,sender=context.return_value.Pipe.return_value=(Mock(),Mock())
            receiver.poll.return_value=False
            process=context.return_value.Process.return_value
            process.is_alive.return_value=False
            with self.assertRaises(TimeoutError):run_limited(spec(),seconds=3600)
            receiver.poll.assert_called_once_with(29.875)
            process.join.assert_called()

    def test_infinite_cpu_loop_is_terminated_without_children_left(self):
        start=time.monotonic()
        with self.assertRaises(TimeoutError):run_limited(spec(),seconds=.8,target=infinite_worker)
        self.assertLess(time.monotonic()-start,4)
        self.assertFalse(multiprocessing.active_children())


if __name__=='__main__':unittest.main()
