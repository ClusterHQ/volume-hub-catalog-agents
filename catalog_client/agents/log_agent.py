# Report flocker-control, flocker-dataset-agent logs
#
# Support Ubuntu, CentOS, and CoreOS (https://clusterhq.com/2015/09/01/flocker-runs-on-coreos/)
#
# Requires /var/run/docker.sock bind-mounted from the host so the Docker API
# can be used to run more containers to collect the logs - which reside on the
# host.

from twisted.internet.defer import DeferredList

from eliot import Message, write_traceback

from .agentlib import agent_main
from ._dockerlogs import _DockerCollector
from ._filelogs import _SyslogCollector
from ._journallogs import _JournaldCollector

def main():
    collector = _Collector()
    return agent_main(collector)

class NoApplicableDetector(Exception):
    """
    No collector detected an execution environment to which it is suited.
    """

class _Collector(object):
    name = b"log"

    _COLLECTORS = [
        # Order matters.
        _SyslogCollector(),
        _JournaldCollector(),

        # XXX This one is broken.  It hangs after a while.  Make uft CoreOS
        # configure Docker to send container logs to journald.
        _DockerCollector(),
    ]

    _collector = None

    def _filter_detection(self, detection_results):
        applicable = []
        for collector, (success, detection_result) in zip(self._COLLECTORS, detection_results):
            if success:
                if detection_result:
                    applicable.append(collector)
            else:
                write_traceback(
                    system="log-agent:os-detection",
                    collector=collector.__class__.__name__,
                )
        return applicable

    def _pick_collector(self, applicable):
        if len(applicable) == 0:
            raise NoApplicableDetector()
        elif len(applicable) != 1:
            Message.new(
                system="log-agent:os-detection:multiples",
                collectors=list(
                    collector.__class__.__name__ for collector in applicable
                ),
            ).write()
        else:
            Message.new(
                system="log-agent:os-detection",
                collector=applicable[0].__class__.__name__,
            ).write()

        collector = applicable[0]
        return collector

    def _discover_mode(self):
        detecting = DeferredList(
            list(
                collector.detect()
                for collector
                in self._COLLECTORS
            )
        )
        detecting.addCallback(self._filter_detection)
        detecting.addCallback(self._pick_collector)

        def save_collector(collector):
            self._collector = collector
        detecting.addCallback(save_collector)

        return detecting

    def collect(self):
        if self._collector is None:
            d = self._discover_mode()
            d.addCallback(lambda ignored: self.collect())
            return d

        return self._collector.collect()

