# Run a loop:
#
#  - ask Docker what containers it knows about and gets some details
#    about their state
#
#  - send that information to Firehose server

from __future__ import print_function

from datetime import timedelta
from os import environ
import docker
import treq
import sys
import json

from OpenSSL.crypto import FILETYPE_PEM, load_certificate

from eliot import write_traceback, to_file

from pyrsistent import PClass, PMap, pmap, field, thaw

from twisted.python.filepath import FilePath
from twisted.python.log import startLogging
from twisted.internet.defer import succeed
from twisted.internet.task import LoopingCall, react

DEFAULT_FIREHOSE_HOSTNAME = b"firehose.volumehub.io"
DEFAULT_FIREHOSE_PORT = 443
DEFAULT_FIREHOSE_PROTOCOL = "https"

REPORT_INTERVAL = timedelta(seconds=5.0)

def main():
    to_file(sys.stdout)
    startLogging(sys.stdout)
    return react(
        run_agent, [
            environ.get(
                "FLOCKER_CONFIGURATION_PATH",
                "/etc/flocker",
            ).decode("ascii"),
            environ.get(
                "CATALOG_FIREHOSE_PROTOCOL",
                DEFAULT_FIREHOSE_PROTOCOL,
            ).decode("ascii"),
            environ.get(
                "CATALOG_FIREHOSE_HOSTNAME",
                DEFAULT_FIREHOSE_HOSTNAME,
            ).decode("ascii"),
            int(
                environ.get(
                    "CATALOG_FIREHOSE_PORT",
                    unicode(DEFAULT_FIREHOSE_PORT).encode("ascii"),
                ).decode("ascii")
            ),
            environ["CATALOG_FIREHOSE_SECRET"].decode("ascii"),
        ],
    )


class Collector(object):
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


class Reporter(PClass):
    common = field(type=PMap, factory=pmap, mandatory=True)
    location = field(type=unicode, mandatory=True)

    def report(self, result):
        result = self.common.set("result", result)
        return treq.post(
            self.location.encode("ascii"),
            json.dumps(thaw(result)),
            timeout=30,
        )


class StdoutReporter(PClass):
    common = field(type=PMap, factory=pmap, mandatory=True)

    def report(self, result):
        result = self.common.set("result", result)
        sys.stdout.write(json.dumps(thaw(result)) + "\n")
        sys.stdout.flush()


def find_identifiers(config_path):
    node_cert_path = config_path.child(b"node.crt")
    if node_cert_path.exists():
        node_pem = node_cert_path.getContent()
        node_cert = load_certificate(FILETYPE_PEM, node_pem)

        node_uuid = node_cert.get_subject().CN.decode("ascii")[len(u"node-"):]
        cluster_uuid = node_cert.get_subject().OU.decode("ascii")
        return pmap({u"node-uuid": node_uuid, u"cluster-uuid": cluster_uuid})

    control_cert_path = config_path.child(b"control-service.crt")
    if control_cert_path.exists():
        control_pem = control_cert_path.getContent()
        control_cert = load_certificate(FILETYPE_PEM, control_pem)

        cluster_uuid = control_cert.get_subject().OU.decode("ascii")
        return pmap({u"control-service": True, u"cluster-uuid": cluster_uuid})

    raise Exception(
        "Couldn't figure out where this is running, "
        "looked for node.crt and control-service.crt in {}".format(
            config_path.path
        )
    )


def run_agent(reactor, config_path, protocol, firehose, port, secret):
    identifiers = find_identifiers(FilePath(config_path))
    common = identifiers.set(u"secret", secret)
    location = u"{protocol}://{host}:{port}/v1/firehose/docker".format(
        protocol=protocol, host=firehose, port=port,
    )
    reporter = Reporter(location=location, common=common)
    # reporter = StdoutReporter(common=common)

    collector = Collector()

    loop = LoopingCall(lambda: collector.collect().addCallback(reporter.report))
    return loop.start(REPORT_INTERVAL.total_seconds(), now=True)
