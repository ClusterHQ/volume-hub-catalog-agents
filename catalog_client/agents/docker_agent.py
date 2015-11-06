# Run a loop:
#
#  - ask Docker what containers it knows about and gets some details
#    about their state
#
#  - send that information to Firehose server

from __future__ import print_function

import docker
from twisted.internet.defer import succeed

from eliot import write_traceback

from .agentlib import agent_main

def main():
    return agent_main(Collector())


class Collector(object):
    name = b"docker"

    def __init__(self):
        self._client = docker.client.Client(version="1.19")

    def _get_container_details(self, container_ids):
        for identity in container_ids:
            try:
                yield self._client.inspect_container(identity)
            except:
                write_traceback()


    def collect(self):
        all_containers = self._client.containers(all=True)
        all_container_details = self._get_container_details(
            container[u"Id"] for container in all_containers
        )
        return succeed(dict(
            docker_info=list(all_container_details),
            docker_version=self._client.version(),
        ))
