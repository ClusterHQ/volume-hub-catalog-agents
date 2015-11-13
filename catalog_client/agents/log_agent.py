# Report flocker-control, flocker-dataset-agent logs
#
# Goals: support Ubuntu, CentOS, and CoreOS
# (https://clusterhq.com/2015/09/01/flocker-runs-on-coreos/)
#
# Requires / from the host bind-mounted at /host to dig around the various
# places logs can be found on those platforms.

import json

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
        combined = zip(self._COLLECTORS, detection_results)
        for collector, (success, detection_result) in combined:
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

        collecting = self._collector.collect()
        filtering = collecting.addCallback(self._filter_entries)
        return filtering

    def _filter_entries(self, entries):
        """
        :param dict entries: A mapping from unit name to lists of log lines.

        :return: A mapping from unit name to lists of log lines.  Lines
            matching certain patterns may be removed or modified.
        """
        return {
            (unit, self._filter_log_lines(log_lines))
            for (unit, log_lines)
            in entries.items()
        }

    def _filter_log_lines(self, log_lines):
        """
        :param list log_lines: A list of bytes giving lines from some unit's
            log.

        :return: The same as ``log_lines`` but with certain information removed
            or munged.
        """
        for log_line in log_lines:
            munged = self._munge_one_line(log_line)
            if munged is not None:
                yield munged

    def _munge_one_line(self, log_line):
        """
        :param bytes log_line: One line from some unit's log.

        :return: Either the log line, unmodified, or a modified version of the
            log line if it contained sensitive information that it would be
            better not to export from this machine.
        """
        try:
            log_obj = json.loads(log_line)
        except:
            # If we can't parse it as JSON then it isn't an Eliot log message.
            # We don't care about filtering anything that's not an Eliot log
            # message.
            return log_line
        else:
            if log_obj.get(u"action_type", None) == u"flocker:agent:converge":
                cluster_state = log_obj.get(u"cluster_state")
                if cluster_state is not None:
                    log_obj[u"cluster_state"] = self._cleanup_cluster_state(
                        cluster_state
                    )
            return json.dumps(log_obj)
