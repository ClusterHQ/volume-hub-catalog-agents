from twisted.python.filepath import FilePath
from twisted.internet.defer import succeed
from twisted.internet.task import LoopingCall
from twisted.internet.threads import deferToThreadPool

from docker import Client

from ._loglib import _MultiStreamRecorder, _MultiStreamCollector

class _DockerCollector(object):
    _COREOS_PATH = FilePath(b"/host/etc/coreos/update.conf")

    _CONTAINER_NAMES = {
        "flocker-dataset-agent", "flocker-container-agent", "flocker-control",
    }

    _log_streams = None

    def detect(self):
        # Flocker only runs in Docker on CoreOS so far.
        return succeed(self._COREOS_PATH.exists())

    def collect(self):
        if self._log_streams is None:
            self._log_streams, self._recorder = self._start_log_streams()

        return succeed(self._recorder.consume())

    def _start_log_streams(self):
        recorder = _MultiStreamRecorder()

        log_streams = list(
            _DockerLogStream(
                docker_client=Client(base_url=b"unix://host/var/run/docker.sock"),
                reactor=self.reactor,
                container_id=container_name,
                record_log=recorder.recorder(container_name),
            )
            for container_name
            in self._CONTAINER_NAMES
        )
        return (
            _MultiStreamCollector.from_log_streams(log_streams),
            recorder,
        )

class _DockerLogStream(object):
    """
    Collect logs from one Docker container using the Docker API.
    """
    loop = None

    def __init__(self, docker_client, reactor, container_id, record_log):
        self.docker_client = docker_client
        self.reactor = reactor
        self.container_id = container_id
        self.record_log = record_log
        self.log_stream = self.docker_client.logs(
            # http://docker-py.readthedocs.org/en/1.5.0/api/#logs
            #
            # The stream parameter makes the logs function return a blocking
            # generator you can iterate over to retrieve log output as it
            # happens.
            #
            # timestamps (bool): Show timestamps
            #
            # tail (str or int): Output specified number of lines at the end of
            # logs: "all" or number. Default "all"
            #
            # stdout (bool): Get STDOUT
            #
            # stderr (bool): Get STDERR
            #
            # container (str): The container to get logs from
            stream=True, timestamps=False, tail=0,
            container=self.container_id,
        )

    def run(self):
        self.loop = LoopingCall(
            self._next, self.log_stream
        )
        return self.loop.start(0.0, now=True)

    def _next(self, log_stream):
        d = deferToThreadPool(
            self.reactor, self.reactor.getThreadPool(), next, self.log_stream,
        )
        def record_it(log_event):
            self.record_log(log_event)
        d.addCallback(record_it)
        return d
