#
# This file is part of YaRSS2 and is licensed under GNU General Public License 3.0, or later, with
# the additional special exception to link portions of this program with the OpenSSL library.
# See LICENSE for more details.
#

import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from unittest import mock

from twisted.trial import unittest

from deluge_yarss2 import atoma
from deluge_yarss2.rssfeed_handling import RSSFeedHandler
from deluge_yarss2.util import http, logging
from deluge_yarss2.yarss_config import get_fresh_rssfeed_config, get_fresh_subscription_config, get_user_agent

from .utils.log_utils import plugin_tests_logger_name

log = logging.getLogger(plugin_tests_logger_name)

FEED_PATH = "/feed.xml"
ETAG = '"feed-v1"'
REPLACED_ETAG = '"feed-v1-replaced"'
LAST_MODIFIED = "Sun, 21 Oct 2012 21:47:35 GMT"

FEED_BODY = b"""<?xml version="1.0" encoding="UTF-8" ?>
<rss version="2.0">
  <channel>
    <title>YaRSS2 Test feed</title>
    <link>https://site.net</link>
    <description>This is a test feed for YaRSS2!</description>
    <ttl>30</ttl>
    <item>
      <title>This is the title</title>
      <link>https://site.net/file.torrent</link>
      <pubDate>Sun, 21 Oct 2012 21:47:35 -0000</pubDate>
    </item>
  </channel>
</rss>
"""


class ConditionalFeedRequestHandler(BaseHTTPRequestHandler):
    """Serves `FEED_BODY`, records the headers of each request in the server's `requests` list,
    and answers `304 Not Modified` to a request whose `If-None-Match` matches either ETag,
    with the server's `not_modified_etag`.
    Sends the validators only if the server's `send_validators` is true."""

    def do_GET(self):  # noqa: N802
        # The `HTTPMessage` looks up header names case-insensitively, as urllib capitalizes them.
        self.server.requests.append(self.headers)
        if self.server.send_validators and self.headers.get("If-None-Match") in (ETAG, REPLACED_ETAG):
            self.send_response(304)
            self.send_header("ETag", self.server.not_modified_etag)
            self.end_headers()
            return
        self.send_response(200)
        self.send_header("Content-Type", "application/rss+xml")
        self.send_header("Content-Length", str(len(FEED_BODY)))
        if self.server.send_validators:
            self.send_header("ETag", ETAG)
            self.send_header("Last-Modified", LAST_MODIFIED)
        self.end_headers()
        self.wfile.write(FEED_BODY)

    def log_message(self, format, *args):
        pass


class ConditionalFeedRequestsTestCase(unittest.TestCase):
    def setUp(self):  # NOQA
        self.server = self.start_http_server()
        self.feed_url = f"http://127.0.0.1:{self.server.server_address[1]}{FEED_PATH}"
        self.handler = RSSFeedHandler(log)
        self.rssfeed = get_fresh_rssfeed_config(name="Test feed", url=self.feed_url, key="0")
        self.subscription = get_fresh_subscription_config(
            name="Test subscription",
            rssfeed_key="0",
            regex_include="title",
            last_match="2000-01-01T00:00:00+00:00",
            key="0",
        )
        self.config = {
            "rssfeeds": {"0": self.rssfeed},
            "subscriptions": {"0": self.subscription},
            "cookies": {},
        }

    def start_http_server(self):
        server = ThreadingHTTPServer(("127.0.0.1", 0), ConditionalFeedRequestHandler)
        server.requests = []
        server.send_validators = True
        server.not_modified_etag = ETAG
        # A short poll interval keeps `shutdown`, which waits for the next poll, from slowing down every test.
        thread = threading.Thread(target=server.serve_forever, kwargs={"poll_interval": 0.05})
        thread.start()
        self.addCleanup(thread.join)
        self.addCleanup(server.server_close)
        self.addCleanup(server.shutdown)
        return server

    def run_feed(self):
        return self.handler.fetch_feed_torrents(self.config, "0")

    def assert_unconditional(self, request):
        self.assertNotIn("If-None-Match", request)
        self.assertNotIn("If-Modified-Since", request)

    def assert_conditional(self, request):
        self.assertEqual(request.get("If-None-Match"), ETAG)
        self.assertEqual(request.get("If-Modified-Since"), LAST_MODIFIED)

    def test_second_run_is_conditional_and_matches_the_cached_items(self):
        first = self.run_feed()
        second = self.run_feed()

        first_request, second_request = self.server.requests
        self.assert_unconditional(first_request)
        self.assert_conditional(second_request)
        self.assertEqual(len(first["matching_torrents"]), 1)
        self.assertEqual(second["matching_torrents"], first["matching_torrents"])
        self.assertEqual(second["rssfeed_items"], first["rssfeed_items"])

    def test_not_modified_response_is_not_parsed(self):
        self.run_feed()
        with mock.patch.object(atoma, "parse_rss_bytes", wraps=atoma.parse_rss_bytes) as parse:
            fetch_data = self.run_feed()

        self.assert_conditional(self.server.requests[1])
        parse.assert_not_called()
        self.assertEqual(len(fetch_data["matching_torrents"]), 1)

    def test_not_modified_response_keeps_the_ttl(self):
        self.rssfeed["obey_ttl"] = True
        first = self.run_feed()
        second = self.run_feed()

        self.assert_conditional(self.server.requests[1])
        self.assertEqual(first["ttl"], 30)
        self.assertEqual(second["ttl"], 30)
        self.assertIs(self.rssfeed["obey_ttl"], True)

    def test_not_modified_response_replaces_the_etag(self):
        self.server.not_modified_etag = REPLACED_ETAG
        self.run_feed()
        self.run_feed()
        self.run_feed()

        self.assert_conditional(self.server.requests[1])
        self.assertEqual(self.server.requests[2].get("If-None-Match"), REPLACED_ETAG)
        self.assertEqual(self.server.requests[2].get("If-Modified-Since"), LAST_MODIFIED)

    def test_changed_url_sends_no_validators(self):
        self.run_feed()
        self.run_feed()
        self.rssfeed["url"] = self.feed_url + "?changed"
        self.run_feed()

        self.assert_conditional(self.server.requests[1])
        self.assert_unconditional(self.server.requests[2])

    def test_changed_user_agent_sends_no_validators(self):
        self.run_feed()
        self.run_feed()
        self.rssfeed["user_agent"] = "Changed agent"
        self.run_feed()

        self.assert_conditional(self.server.requests[1])
        self.assert_unconditional(self.server.requests[2])

    def test_preview_neither_uses_nor_fills_the_cache(self):
        # Called as the subscription dialog calls `Core.get_rssfeed_parsed`, with the client's copy
        # of the feed config and the same cookies and user agent as the scheduled run
        preview_data = dict(self.rssfeed)
        site_cookies_dict = http.get_matching_cookies_dict(self.config["cookies"], preview_data["site"])
        user_agent = get_user_agent(rssfeed_data=preview_data)
        self.handler.get_rssfeed_parsed(preview_data, site_cookies_dict=site_cookies_dict, user_agent=user_agent)
        self.run_feed()
        self.run_feed()
        self.handler.get_rssfeed_parsed(preview_data, site_cookies_dict=site_cookies_dict, user_agent=user_agent)
        self.run_feed()

        preview_request, first_run, second_run, second_preview, third_run = self.server.requests
        self.assert_unconditional(preview_request)
        self.assert_unconditional(first_run)
        self.assert_conditional(second_run)
        self.assert_unconditional(second_preview)
        self.assert_conditional(third_run)

    def test_response_without_validators_gets_no_conditional_request(self):
        self.server.send_validators = False
        first = self.run_feed()
        second = self.run_feed()

        for request in self.server.requests:
            self.assert_unconditional(request)
        self.assertEqual(len(first["matching_torrents"]), 1)
        self.assertEqual(second["matching_torrents"], first["matching_torrents"])

    def test_runs_add_no_config_keys(self):
        rssfeed_keys = set(self.rssfeed)
        subscription_keys = set(self.subscription)
        config_keys = set(self.config)
        self.run_feed()
        self.run_feed()

        self.assert_conditional(self.server.requests[1])
        self.assertEqual(set(self.rssfeed), rssfeed_keys)
        self.assertEqual(set(self.subscription), subscription_keys)
        self.assertEqual(set(self.config), config_keys)
