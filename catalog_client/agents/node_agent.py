# Collect Flocker version

from os import environ

from twisted.internet.utils import getProcessOutput

from .agentlib import agent_main


def main():
    return agent_main(_Collector())


class _Collector(object):
    name = b"node"

    def collect(self):
        return getProcessOutput(
            b"chroot", [b"/host", b"flocker-diagnostics", b"--version"],
            env=environ,
        )
