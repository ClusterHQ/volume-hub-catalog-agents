from twisted.python.filepath import FilePath
from twisted.internet.defer import succeed
from twisted.internet.task import LoopingCall, deferLater
from twisted.internet.threads import deferToThreadPool
from twisted.internet import reactor

from eliot import Message, write_traceback

from docker import Client
from docker.errors import NotFound

from ._loglib import _MultiStreamRecorder, _MultiStreamCollector

class _DockerCollector(object):
    _COREOS_PATH = FilePath(b"/host/etc/coreos/update.conf")

    _CONTAINER_NAMES = {
        "flocker-dataset-agent", "flocker-container-agent", "flocker-control",
    }

    _log_streams = None

    reactor = reactor

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
    log_stream = None

    def __init__(self, docker_client, reactor, container_id, record_log):
        self.docker_client = docker_client
        self.reactor = reactor
        self.container_id = container_id
        self.record_log = record_log

    def _open_log_stream(self):
        return self.docker_client.logs(
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
            #
            # tail=1 because https://github.com/docker/docker-py/issues/845
            stream=True, timestamps=False, tail=1,
            container=self.container_id,
        )

    def run(self):
        self.loop = LoopingCall(self._next)
        return self.loop.start(5.0, now=True)

    def _next(self):
        def maybe_open_then_iterate(log_stream):
            if log_stream is None:
                # Try opening the stream any time we don't already have it
                # open.  Maybe the container we're watching went away for a
                # minute and is going to come back.
                try:
                    log_stream = self._open_log_stream()
                except NotFound:
                    Message.new(
                        system="log-agent:docker-collector:open:failed",
                        container=self.container_id,
                        reason="not found",
                    ).write()
                    return None
                except:
                    write_traceback(
                        system="log-agent:docker-collector:open:failed",
                        container=self.container_id,
                    )
                    return None
                else:
                    Message.new(
                        system="log-agent:docker-collector:open:succeeded",
                        container=self.container_id,
                    ).write()

            logchunk = next(log_stream)
            return (logchunk, log_stream)


        d = deferToThreadPool(
            self.reactor, self.reactor.getThreadPool(),
            maybe_open_then_iterate, self.log_stream,
        )
        def record_it(iterate_result):
            if iterate_result is None:
                # Couldn't open the log stream.  Delay future attempts by a
                # little longer than normal.
                return deferLater(self.reactor, 60, lambda: None)
            log_event, self.log_stream = iterate_result
            if log_event:
                self.record_log(log_event)
        d.addCallback(record_it)
        return d
