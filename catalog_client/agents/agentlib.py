
from datetime import timedelta
from os import environ
import sys

import treq
from treq.client import HTTPClient
import json

from OpenSSL.crypto import FILETYPE_PEM, load_certificate

from eliot import to_file, start_action
from eliot.twisted import DeferredContext

from twisted.internet.task import LoopingCall, react
from twisted.python.filepath import FilePath
from twisted.internet import reactor, ssl
from twisted.web.client import Agent
from twisted.python.log import startLogging

import yaml

from pyrsistent import PClass, PMap, pmap, field, thaw

DEFAULT_FIREHOSE_HOSTNAME = b"firehose-volumehub.clusterhq.com"
DEFAULT_FIREHOSE_PORT = 443
DEFAULT_FIREHOSE_PROTOCOL = "https"

REPORT_INTERVAL = timedelta(seconds=5.0)



def get_client(reactor=reactor, certificates_path=FilePath("/etc/flocker"),
        user_certificate_filename="plugin.crt", user_key_filename="plugin.key",
        cluster_certificate_filename="cluster.crt", target_hostname=None):
    """
    Create a ``treq``-API object that implements the REST API TLS
    authentication.

    That is, validating the control service as well as presenting a
    certificate to the control service for authentication.

    :return: ``treq`` compatible object.
    """
    if target_hostname is None:
        config = certificates_path.child("agent.yml")
        if config.exists():
            agent_config = yaml.load(config.open())
            target_hostname = agent_config["control-service"]["hostname"]

    user_crt = certificates_path.child(user_certificate_filename)
    user_key = certificates_path.child(user_key_filename)
    cluster_crt = certificates_path.child(cluster_certificate_filename)

    if (user_crt.exists() and user_key.exists() and cluster_crt.exists()
            and target_hostname is not None):
        # we are installed on a flocker node with a certificate, try to reuse
        # it for auth against the control service
        cert_data = cluster_crt.getContent()
        auth_data = user_crt.getContent() + user_key.getContent()

        authority = ssl.Certificate.loadPEM(cert_data)
        client_certificate = ssl.PrivateCertificate.loadPEM(auth_data)

        class ContextFactory(object):
            def getContext(self, hostname, port):
                context = client_certificate.options(authority).getContext()
                return context

        return HTTPClient(Agent(reactor, contextFactory=ContextFactory()))
    else:
        raise Exception("Not enough information to construct TLS context: "
                "user_crt: %s, cluster_crt: %s, user_key: %s, target_hostname: %s" % (
                    user_crt, cluster_crt, user_key, target_hostname))



class Reporter(PClass):
    common = field(type=PMap, factory=pmap, mandatory=True)
    location = field(type=unicode, mandatory=True)

    def report(self, result):
        result = self.common.set("result", result)
        context = start_action(system="reporter:post")
        with context.context():
            posting = DeferredContext(
                treq.post(
                    self.location.encode("ascii"),
                    json.dumps(thaw(result)),
                    timeout=30,
                )
            )
            return posting.addActionFinish()


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

def _maybe_report(result, reporter):
    if result:
        return reporter.report(result)
    return None

def run_agent(reactor, config_path, protocol, firehose, port, secret, collector):
    identifiers = find_identifiers(FilePath(config_path))
    # Base64 encoded so it is valid json
    common = identifiers.set(u"secret", secret)
    location = u"{protocol}://{host}:{port}/v1/firehose/{collector}".format(
        protocol=protocol, host=firehose, port=port, collector=collector.name,
    )
    reporter = Reporter(location=location, common=common)
    # reporter = StdoutReporter(common=common)

    loop = LoopingCall(lambda: collector.collect().addCallback(_maybe_report, reporter))
    # TODO Capped exponential backoff on errors from the server
    return loop.start(REPORT_INTERVAL.total_seconds(), now=True)


def agent_main(collector):
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
            # Base64 encoded
            environ["CATALOG_FIREHOSE_SECRET"].decode("ascii"),
            collector,
        ],
    )
