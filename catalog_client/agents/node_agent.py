# Collect Flocker version

from twisted.internet.utils import getProcessOutput

from .agentlib import agent_main


def main():
    return agent_main(_Collector())


class _Collector(object):
    def collect(self):
        return getProcessOutput(
            b"chroot", [b"/host", b"flocker-diagnostics", b"--version"]
        )
