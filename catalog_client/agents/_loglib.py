from functools import partial

from twisted.internet.task import LoopingCall
from twisted.internet.defer import succeed

from eliot import write_failure

class _MultiStreamCollector(object):
    def __init__(self, log_streams):
        self.log_streams = log_streams

    @classmethod
    def from_log_streams(cls, log_streams):
        self = cls(log_streams)
        for log_stream in log_streams:
            call = LoopingCall(self._run_stream, log_stream)
            d = call.start(0.0, now=True)
            d.addErrback(write_failure)
        return self

    def _run_stream(self, log_stream):
        d = log_stream.run()
        d.addErrback(write_failure)
        return d

class _MultiStreamRecorder(object):
    def __init__(self):
        self._logs = []

    def recorder(self, key):
        return partial(self._record_log, key)

    def consume(self):
        result = self._logs
        self._logs = {}
        return succeed(result)

    def _record_log(self, key, log_event):
        self._logs.setdefault(key, []).append(log_event)