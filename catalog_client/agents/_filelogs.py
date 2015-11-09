from twisted.python.filepath import FilePath
from twisted.internet.task import LoopingCall

from ._loglib import _MultiStreamRecorder, _MultiStreamCollector

class _SyslogCollector(object):
    _LOG_PATHS = {
        # The paths we configure Flocker to log to in the upstart configuration
        # file.  See Flocker/admin/package-files/upstart/flocker-*.conf
        FilePath(b"/var/log/flocker/flocker-dataset-agent.log"),
        FilePath(b"/var/log/flocker/flocker-control.log"),
    }

    def detect(self):
        return any(path.exists() for path in self._LOG_PATHS)

    def collect(self):
        if self._log_streams is None:
            self._log_streams, self._recorder = self._start_log_streams()

        return self._recorder.consume()

    def _start_log_streams(self):
        recorder = _MultiStreamRecorder()
        log_streams = list(
            _FileLogStream(
                path=path,
                record_log=recorder.recorder(path.basename())
            )
            for path
            in self._LOG_PATHS
        )
        return (
            _MultiStreamCollector.from_log_streams(log_streams),
            recorder,
        )

class _FileLogStream(object):
    def __init__(self, path, record_log):
        self.path = path
        self.record_log = record_log
        self.log_file = self.path.open()

    def run(self):
        self.loop = LoopingCall(self._next, self.log_file)
        return self.loop.start(1.0, now=True)

    def _next(self, log_file):
        # Try to read more than one line per iteration but also try to avoid
        # doing an unbounded amount of work.  100 lines is picked out of a hat.
        for i in range(100):
            line = log_file.readline()
            if line:
                self.record_log(line)
            else:
                break
