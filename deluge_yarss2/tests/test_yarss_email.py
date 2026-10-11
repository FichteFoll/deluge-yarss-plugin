#
# Copyright (C) 2012-2019 bendikro bro.devel+yarss2@gmail.com
#
# This file is part of YaRSS2 and is licensed under GNU General Public License 3.0, or later, with
# the additional special exception to link portions of this program with the OpenSSL library.
# See LICENSE for more details.
#

import base64
import smtplib

from twisted.trial import unittest

import deluge_yarss2.yarss_config
from deluge_yarss2.torrent_handling import TorrentHandler
from deluge_yarss2.util import logging, yarss_email
from deluge_yarss2.util.yarss_email import send_email, send_torrent_email

from . import common as test_common
from .utils.log_utils import plugin_tests_logger_name

log = logging.getLogger(plugin_tests_logger_name)

smtp = None
inbox = []


def base64_encoded(msg_str):
    msg_bytes = msg_str.encode()
    msg_base64_bytes = base64.b64encode(msg_bytes)
    msg_base64_str = msg_base64_bytes.decode()
    return msg_base64_str


class Message:
    def __init__(self, from_address, to_address, message):
        self.from_address = from_address
        self.to_address = to_address
        self.message = message


class DummySMTP:
    def __init__(self, server_address, port, timeout=None):
        self.server_address = server_address
        self.port = port
        self.timeout = timeout
        global smtp
        smtp = self
        self.ehlo_called = False
        self.starttls_called = False
        self.closed = False

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.closed = True

    def login(self, username, password):
        self.username = username
        self.password = password

    def sendmail(self, from_address, to_address, fullmessage):
        global inbox
        # This hack is necessary to on python3 to make the output equal the python2 output
        fullmessage = fullmessage.replace("; boundary=", ";\nboundary=")
        inbox.append(Message(from_address, to_address, fullmessage))
        return []

    def quit(self):
        self.has_quit = True
        self.closed = True

    def ehlo(self):
        self.ehlo_called = True

    def starttls(self):
        self.starttls_called = True

    def get_emails(self):
        global inbox
        return inbox


smtplib.SMTP = DummySMTP


class YaRSS2EmailTestCase(unittest.TestCase):
    def setUp(self):  # NOQA
        self.config = test_common.get_test_config()

    def test_send_email(self):
        email_config = deluge_yarss2.yarss_config.get_fresh_email_config()
        email_config["from_address"] = "from@test.com"

        email = {}
        email["to_address"] = "test@address.com"
        email["subject"] = "Test Subject"
        email["message"] = "Test Message"

        global smtp
        global inbox
        self.assertTrue(send_email(email, email_config))
        self.assertEqual(inbox[0].from_address, email_config["from_address"])
        self.assertEqual(inbox[0].to_address, email["to_address"])
        self.assertEqual(smtp.server_address, email_config["smtp_server"])
        self.assertEqual(smtp.port, smtplib.SMTP_PORT)

    def test_send_email_with_auth(self):
        email_config = deluge_yarss2.yarss_config.get_fresh_email_config()
        email_config["from_address"] = "from@test.com"
        email_config["smtp_server"] = "server_address"
        email_config["smtp_port"] = "43353"
        email_config["smtp_authentication"] = True
        email_config["smtp_username"] = "testuser"
        email_config["smtp_password"] = "testpw"

        email = {}
        email["to_address"] = "test@address.com"
        email["subject"] = "Test Subject"
        email["message"] = "Test Message"

        global smtp
        global inbox
        self.assertTrue(send_email(email, email_config))
        self.assertEqual(inbox[0].from_address, email_config["from_address"])
        self.assertEqual(inbox[0].to_address, email["to_address"])
        self.assertEqual(smtp.server_address, email_config["smtp_server"])
        self.assertEqual(smtp.port, int(email_config["smtp_port"]))
        self.assertEqual(smtp.username, email_config["smtp_username"])
        self.assertEqual(smtp.password, email_config["smtp_password"])

        self.assertTrue(smtp.ehlo_called)
        self.assertTrue(smtp.starttls_called)

    def test_send_email_html_only(self):
        email_config = deluge_yarss2.yarss_config.get_fresh_email_config()
        email_config["from_address"] = "from@test.com"

        email = {}
        email["to_address"] = "test@address.com"
        email["subject"] = "Test Subject"
        email["message_html"] = "<p>Test Message</p>"

        self.assertTrue(send_email(email, email_config))
        self.assertIn(base64_encoded(email["message_html"]), inbox[-1].message)

    def test_send_email_sendmail_failure_closes_connection(self):
        email_config = deluge_yarss2.yarss_config.get_fresh_email_config()
        email_config["from_address"] = "from@test.com"

        email = {}
        email["to_address"] = "test@address.com"
        email["subject"] = "Test Subject"
        email["message"] = "Test Message"

        def failing_sendmail(self, from_address, to_address, fullmessage):
            raise smtplib.SMTPException("sendmail failed")

        self.patch(DummySMTP, "sendmail", failing_sendmail)

        global smtp
        self.assertFalse(send_email(email, email_config))
        self.assertTrue(smtp.closed)

    def test_send_email_closing_quit_error_returns_false(self):
        email_config = deluge_yarss2.yarss_config.get_fresh_email_config()
        email_config["from_address"] = "from@test.com"

        email = {}
        email["to_address"] = "test@address.com"
        email["subject"] = "Test Subject"
        email["message"] = "Test Message"

        def failing_sendmail(self, from_address, to_address, fullmessage):
            raise smtplib.SMTPException("sendmail failed")

        def failing_exit(self, exc_type, exc_value, traceback):
            self.closed = True
            raise smtplib.SMTPResponseException(421, "Service not available")

        self.patch(DummySMTP, "sendmail", failing_sendmail)
        self.patch(DummySMTP, "__exit__", failing_exit)

        global smtp
        self.assertFalse(send_email(email, email_config))
        self.assertTrue(smtp.closed)

    def test_send_email_passes_timeout(self):
        email_config = deluge_yarss2.yarss_config.get_fresh_email_config()
        email_config["from_address"] = "from@test.com"

        email = {}
        email["to_address"] = "test@address.com"
        email["subject"] = "Test Subject"
        email["message"] = "Test Message"

        global smtp
        self.assertTrue(send_email(email, email_config))
        self.assertEqual(smtp.timeout, yarss_email.SMTP_TIMEOUT)


class YaRSS2TorrentEmailTestCase(unittest.TestCase):
    def setUp(self):  # NOQA
        self.handler = TorrentHandler(log)
        smtplib.SMTP = DummySMTP
        self.email_config = deluge_yarss2.yarss_config.get_fresh_email_config()
        self.email_config["from_address"] = "from@test.com"
        self.email = {}
        self.email["to_address"] = "test@address.com"
        self.email["subject"] = "Test Subject"
        self.email["message"] = "Hi\n\nThis is a test message.\n\n\nRegards"
        self.email["name"] = "Test Message Name"

        self.expected_messsage = []
        self.expected_messsage.append('Content-Type: text/plain; charset="utf-8"')
        self.expected_messsage.append("MIME-Version: 1.0")
        self.expected_messsage.append("Content-Transfer-Encoding: base64")
        self.expected_messsage.append("Subject: %s")
        self.expected_messsage.append("From: %s")
        self.expected_messsage.append("To: %s")

        self.expected_messsage_multipart = []
        self.expected_messsage_multipart.append("Content-Type: multipart/alternative;")
        self.expected_messsage_multipart.append("MIME-Version: 1.0")
        self.expected_messsage_multipart.append("Subject: %s")
        self.expected_messsage_multipart.append("From: %s")
        self.expected_messsage_multipart.append("To: %s")
        self.expected_messsage_multipart.append('Content-Type: text/plain; charset="utf-8"')
        self.expected_messsage_multipart.append("MIME-Version: 1.0")
        self.expected_messsage_multipart.append("Content-Transfer-Encoding: base64")
        self.expected_messsage_multipart.append('Content-Type: text/html; charset="utf-8"')
        self.expected_messsage_multipart.append("MIME-Version: 1.0")
        self.expected_messsage_multipart.append("Content-Transfer-Encoding: base64")

    def record_sent_email_data(self):
        """Record a copy of the data each `send_email` call receives, then send it."""
        sent_email_data = []

        def recording_send_email(email_conf, server_conf):
            sent_email_data.append(dict(email_conf))
            return send_email(email_conf, server_conf)

        self.patch(yarss_email, "send_email", recording_send_email)
        return sent_email_data

    def verify_email_multipart(self, email_message, email, email_config, email_data):
        """
        email_message - a test_yarss_email.Message
        email - a dictionary with the email info
        email_config - a dictionary with the email configuration options
        """
        self.assertEqual(email_message.to_address, email["to_address"])
        lines = email_message.message.splitlines()

        # Content type - multipart
        self.assertEqual(lines[0], self.expected_messsage_multipart[0])
        # MIME version
        self.assertEqual(lines[2], self.expected_messsage_multipart[1])
        # Subject
        self.assertEqual(lines[3], self.expected_messsage_multipart[2] % email["subject"])
        # From address
        self.assertEqual(lines[4], self.expected_messsage_multipart[3] % email_config["from_address"])
        # To address
        self.assertEqual(lines[5], self.expected_messsage_multipart[4] % email["to_address"])
        # Content type text/plain
        self.assertEqual(lines[8], self.expected_messsage_multipart[5])
        # MIME version
        self.assertEqual(lines[9], self.expected_messsage_multipart[6])
        # Content transfer encoding
        self.assertEqual(lines[10], self.expected_messsage_multipart[7])

        # Message content
        index = 12
        message_base64 = ""
        # Get the whole message
        while lines[index].strip() != "":
            message_base64 += lines[index]
            index += 1

        msg_plain_base64 = base64_encoded(email_data["message"])
        self.assertEqual(message_base64, msg_plain_base64)

        # Content type text/html
        self.assertEqual(lines[index + 2], self.expected_messsage_multipart[8])
        # MIME version
        self.assertEqual(lines[index + 3], self.expected_messsage_multipart[9])
        # Content transfer encoding
        self.assertEqual(lines[index + 4], self.expected_messsage_multipart[10])

        message_base64 = ""
        index += 6
        # Get the whole message
        while lines[index].strip() != "":
            message_base64 += lines[index]
            index += 1

        msg_plain_base64 = base64_encoded(email_data["message_html"])
        self.assertEqual(message_base64, msg_plain_base64)

    def verify_email(self, email_message, email, email_config):
        """
        email_message - a test_yarss_email.Message
        email - a dictionary with the email info
        email_config - a dictionary with the email configuration options
        """
        self.assertEqual(email_message.to_address, email["to_address"])
        lines = email_message.message.splitlines()
        # Content type
        self.assertEqual(lines[0], self.expected_messsage[0])
        # MIME version
        self.assertEqual(lines[1], self.expected_messsage[1])
        # Content transfer encoding
        self.assertEqual(lines[2], self.expected_messsage[2])
        # Subject
        self.assertEqual(lines[3], self.expected_messsage[3] % email["subject"])
        # From address
        self.assertEqual(lines[4], self.expected_messsage[4] % email_config["from_address"])
        # To address
        self.assertEqual(lines[5], self.expected_messsage[5] % email["to_address"])

        # Line 7 is the entire message content encoded in base64.
        base64_email_str = base64_encoded(email["message"])
        self.assertEqual(lines[7], base64_email_str)

    def test_send_torrent_email_with_deferred(self):
        def callback(args):
            self.verify_email(smtp.get_emails().pop(), self.email, self.email_config)

        d = send_torrent_email(self.email_config, self.email, deferred=True)
        d.addCallback(callback)
        return d

    def test_send_torrent_email_with_deferred_with_callback(self):
        """This test uses the callback keyword argument to add the callback
        function to the deferred"""

        def callback(args):
            self.verify_email(smtp.get_emails().pop(), self.email, self.email_config)

        d = send_torrent_email(self.email_config, self.email, deferred=True, callback_func=callback)
        return d

    def test_send_torrent_email_multipart_with_deferred(self):
        subscription = {"name": "Subscription name"}
        torrent_names = ["Torrent 1", "Torrent 2"]
        self.email["message"] = "Hi\n\nThis is a test message. \n\n$torrentlist\n\nRegards"
        sent_email_data = self.record_sent_email_data()

        def callback(args):
            message = smtp.get_emails().pop()
            email_data = sent_email_data[-1]
            self.verify_email_multipart(message, self.email, self.email_config, email_data)
            # Verify that the torrent names have been inserted into the message
            self.assertTrue(email_data["message"].find(torrent_names[0]) != -1)
            self.assertTrue(email_data["message"].find(torrent_names[1]) != -1)
            self.assertTrue(email_data["message_html"].find(torrent_names[0]) != -1)
            self.assertTrue(email_data["message_html"].find(torrent_names[1]) != -1)

        # Send email without deferred
        has_sent = send_torrent_email(
            self.email_config,
            self.email,
            torrent_name_list=torrent_names,
            subscription_data=subscription,
            deferred=False,
            callback_func=callback,
        )
        self.assertTrue(has_sent)
        # Send email in
        d = send_torrent_email(
            self.email_config,
            self.email,
            torrent_name_list=torrent_names,
            deferred=True,
            callback_func=callback,
        )
        return d

    def test_send_torrent_email_builds_new_data_per_call(self):
        sent_email_data = self.record_sent_email_data()
        self.email["message"] = "Hi\n\n$torrentlist\n\nRegards"

        send_torrent_email(self.email_config, self.email, torrent_name_list=["Torrent 1"])
        send_torrent_email(self.email_config, self.email)

        self.assertIn("message_html", sent_email_data[0])
        self.assertNotIn("message_html", sent_email_data[1])
        self.assertEqual(sent_email_data[1]["message"], self.email["message"])

    def test_send_torrent_email_escapes_html_part(self):
        sent_email_data = self.record_sent_email_data()
        subscription = {"name": "Tom & Jerry"}
        self.email["subject"] = "New in $subscription_title"
        self.email["message"] = "<b>Hi</b> 1 < 2 in $subscription_title:\n$torrentlist\nBye"

        send_torrent_email(
            self.email_config, self.email, subscription_data=subscription, torrent_name_list=["<b>x</b>"]
        )

        email_data = sent_email_data[0]
        self.assertEqual(email_data["subject"], "New in Tom & Jerry")
        self.assertEqual(email_data["message"], "<b>Hi</b> 1 < 2 in Tom & Jerry:\n * <b>x</b>\n\nBye")
        # The template is trusted and kept as is; only feed-provided torrent names
        # and the subscription name are escaped.
        self.assertEqual(
            email_data["message_html"],
            "<b>Hi</b> 1 < 2 in Tom &amp; Jerry:<br/><ul><li>&lt;b&gt;x&lt;/b&gt; </li></ul>Bye",
        )
