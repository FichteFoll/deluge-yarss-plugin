#
# This file is part of YaRSS2 and is licensed under GNU General Public License 3.0, or later, with
# the additional special exception to link portions of this program with the OpenSSL library.
# See LICENSE for more details.
#

import datetime
import ipaddress
import pathlib
import ssl
import tempfile
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.x509.oid import NameOID
from twisted.trial import unittest

import deluge_yarss2.util.common
from deluge_yarss2.torrent_handling import TorrentHandler
from deluge_yarss2.util import logging

from . import common as test_common
from .utils.log_utils import plugin_tests_logger_name

log = logging.getLogger(plugin_tests_logger_name)


def write_self_signed_certificate(directory):
    """Writes a self-signed certificate for `localhost` and `127.0.0.1` with its key into `directory`.

    Returns the paths of the certificate and the key file.
    """
    # An EC key is generated much faster than an RSA key.
    key = ec.generate_private_key(ec.SECP256R1())
    name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "localhost")])
    now = datetime.datetime.now(datetime.UTC)
    certificate = (
        x509.CertificateBuilder()
        .subject_name(name)
        .issuer_name(name)
        .public_key(key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(now - datetime.timedelta(minutes=1))
        .not_valid_after(now + datetime.timedelta(days=1))
        .add_extension(
            x509.SubjectAlternativeName([x509.DNSName("localhost"), x509.IPAddress(ipaddress.ip_address("127.0.0.1"))]),
            critical=False,
        )
        .sign(key, hashes.SHA256())
    )
    cert_path = pathlib.Path(directory, "cert.pem")
    key_path = pathlib.Path(directory, "key.pem")
    cert_path.write_bytes(certificate.public_bytes(serialization.Encoding.PEM))
    key_path.write_bytes(
        key.private_bytes(serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8, serialization.NoEncryption())
    )
    return cert_path, key_path


class StaticFileRequestHandler(BaseHTTPRequestHandler):
    """Serves the `(content_type, body)` entries of the server's `files` dict by path."""

    def do_GET(self):  # noqa: N802
        if self.path not in self.server.files:
            self.send_error(404)
            return
        content_type, body = self.server.files[self.path]
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format, *args):
        pass


class HTTPSServerTestCase(unittest.TestCase):
    """Serves the test torrent file and the test RSS feed over HTTPS with a self-signed certificate."""

    torrent_path = "/file.torrent"
    feed_path = "/feed.xml"

    def setUp(self):  # NOQA
        torrent_filename = deluge_yarss2.util.common.get_resource(
            "FreeBSD-9.0-RELEASE-amd64-dvd1.torrent", path="tests/data/"
        )
        feed_filename = deluge_yarss2.util.common.get_resource(test_common.testdata_rssfeed_filename, path="tests")
        self.torrent_data = pathlib.Path(torrent_filename).read_bytes()
        self.feed_data = pathlib.Path(feed_filename).read_bytes()
        self.server = self.start_https_server(
            {
                self.torrent_path: ("application/x-bittorrent", self.torrent_data),
                self.feed_path: ("application/rss+xml", self.feed_data),
            }
        )
        self.base_url = f"https://127.0.0.1:{self.server.server_address[1]}"
        self.torrent_url = self.base_url + self.torrent_path
        self.feed_url = self.base_url + self.feed_path

    def start_https_server(self, files):
        with tempfile.TemporaryDirectory() as directory:
            context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
            context.load_cert_chain(*write_self_signed_certificate(directory))
        server = ThreadingHTTPServer(("127.0.0.1", 0), StaticFileRequestHandler)
        # Handshakes run in `accept`, where `socketserver` silently drops those the client aborts.
        server.socket = context.wrap_socket(server.socket, server_side=True)
        server.files = files
        # A short poll interval keeps `shutdown`, which waits for the next poll, from slowing down every test.
        thread = threading.Thread(target=server.serve_forever, kwargs={"poll_interval": 0.05})
        thread.start()
        self.addCleanup(thread.join)
        self.addCleanup(server.server_close)
        self.addCleanup(server.shutdown)
        return server


class DownloadTorrentFileTLSTestCase(HTTPSServerTestCase):
    def setUp(self):  # NOQA
        super().setUp()
        self.handler = TorrentHandler(log)

    def test_download_torrent_file_verifies_certificate(self):
        download = self.handler.download_torrent_file(self.torrent_url)
        self.assertFalse(download.success)
        self.assertIn("certificate verify failed", download.error_msg)

    def test_download_torrent_file_without_verification(self):
        download = self.handler.download_torrent_file(self.torrent_url, verify_tls=False)
        self.assertTrue(download.success)
        self.assertEqual(download.filedump, self.torrent_data)
