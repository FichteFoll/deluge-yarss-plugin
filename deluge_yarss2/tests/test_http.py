#
# Copyright (C) 2012-2019 bendikro bro.devel+yarss2@gmail.com
#
# This file is part of YaRSS2 and is licensed under GNU General Public License 3.0, or later, with
# the additional special exception to link portions of this program with the OpenSSL library.
# See LICENSE for more details.
#

from twisted.trial import unittest

import deluge_yarss2.yarss_config
from deluge_yarss2.util import common, feedparsing, http
from deluge_yarss2.util.feedparsing.encodings import _parse_content_type_header


class HTTPTestCase(unittest.TestCase):
    def setUp(self):  # NOQA
        pass

    def test_encode_cookie_values(self):
        expected = ["key1=value1", "key2=value2", "key3=value3"]
        cookie_pairs = {}
        cookie_pairs["key1"] = "value1"
        cookie_pairs["key2"] = "value2"
        cookie_pairs["key3"] = "value3"
        encoded = http.encode_cookie_values(cookie_pairs)
        self.assertEqual(sorted(encoded.split("; ")), expected)

    def test_get_cookie_header(self):
        url = "http://basename.com/øashdnf/klasflas/dfnmalskdfn/malskdfnmasloal"
        cookies = {}
        cookies["0"] = {"active": True, "site": "basename.com", "value": {"key1": "value1", "key2": "value2"}}
        cookies["1"] = {
            "active": True,
            "site": "non-matching-base-name.com",
            "value": {"key3": "value3", "key4": "value4"},
        }
        cookies["2"] = {"active": False, "site": "basename.com", "value": {"key5": "value5", "key6": "value6"}}
        expected_cookie = "key2=value2; key1=value1"
        header = http.get_cookie_header(cookies, url)
        self.assertTrue("Cookie" in header)
        self.assertEqual(sorted(header["Cookie"].split("; ")), sorted(expected_cookie.split("; ")))

    def test_get_matching_cookies_dict(self):
        cookies = {}
        cookies["0"] = deluge_yarss2.yarss_config.get_fresh_cookie_config()
        cookies["0"]["site"] = "basename.com"
        cookies["0"]["value"]["key1"] = "value1"
        cookies["0"]["value"]["key2"] = "value2"
        cookies["1"] = deluge_yarss2.yarss_config.get_fresh_cookie_config()
        cookies["1"]["site"] = "non-matching_url.com"
        cookies["1"]["value"]["key3"] = "value3"

        matching_cookies = http.get_matching_cookies_dict(cookies, "http://basename.com/blabla")
        self.assertTrue("key1" in matching_cookies)
        self.assertEqual(matching_cookies["key1"], cookies["0"]["value"]["key1"])
        self.assertTrue("key2" in matching_cookies)
        self.assertEqual(matching_cookies["key2"], cookies["0"]["value"]["key2"])
        self.assertFalse("key3" in matching_cookies)

    def test_url_fix(self):
        url = "http://de.wikipedia.org/wiki/Elf (Begriffsklärung)"
        expected = "http://de.wikipedia.org/wiki/Elf%20(Begriffskl%C3%A4rung)"
        result = http.url_fix(url)
        self.assertEqual(expected, result)

    @unittest.SkipTest
    def test_feedparser_ampersant_in_url(self):
        """A bug in feedparser resulted in URL containing &amp when XML Parser was not available.
        This test disables XML Parser and verifies that the URL is correct
        """
        from deluge_yarss2.lib import feedparser

        file_path = common.get_resource("rss_with_ampersand_link.rss", path="tests")
        # This is the link in rss_with_ampersand_link.rss
        expected = "http://hostname.com/Fetch?hash=2f21d4e59&digest=865178f9bc"
        # Disable XML Parser
        feedparser.feedparser._XML_AVAILABLE = 0
        parsed_feeds = feedparser.feedparser.parse(file_path)

        for item in parsed_feeds["items"]:
            self.assertEqual(expected, item["link"])
            break

    def test_clean_html_body(self):
        web_page = """<html>
  <head>
   <title>
    Page title
   </title>
   <style>
    p { color: red; }
   </style>
  </head>
  <body>
   <!-- a comment -->
   <script>
    var x = 1;
   </script>
   <p id="firstpara" align="center">
    This is paragraph
    <b>
     one
    </b>
   </p>
   <p id="secondpara" align="blah">
    This is paragraph
    <b>
     two
    </b>
   </p>
  </body>
 </html>"""
        result = http.clean_html_body(web_page)
        self.assertTrue("This is paragraph" in result)
        self.assertTrue("one" in result)
        self.assertTrue("two" in result)
        self.assertFalse("Page title" in result)
        self.assertFalse("color: red" in result)
        self.assertFalse("var x = 1" in result)
        self.assertFalse("a comment" in result)
        self.assertFalse("\n\n\n" in result)

    def test_clean_html_body_unclosed_head_with_body_tag(self):
        # html5lib ends head mode at the first body content, even without a `</head>`.
        web_page = "<html><head><title>Error</title><body><h1>Forbidden</h1>You are banned</body></html>"
        result = http.clean_html_body(web_page)
        self.assertTrue("Forbidden" in result)
        self.assertTrue("You are banned" in result)
        self.assertFalse("Error" in result)

    def test_clean_html_body_unclosed_head_without_body_tag(self):
        web_page = "<html><head><title>T</title>\n<p>Body text here</p></html>"
        result = http.clean_html_body(web_page)
        self.assertTrue("Body text here" in result)

    def test_clean_html_body_duplicate_head_tag(self):
        web_page = "<head><head><title>T</title></head><body>Body text</body>"
        result = http.clean_html_body(web_page)
        self.assertTrue("Body text" in result)

    def test_clean_html_body_trailing_incomplete_data(self):
        # HTMLParser holds back incomplete trailing data until close().
        result = http.clean_html_body("Rate limited &")
        self.assertTrue("Rate limited &" in result)

    def test_convert_to_utf8_with_declared_charset(self):
        title = "Begriffskl\xe4rung"
        rss = (f"<?xml version='1.0'?><rss><channel><title>{title}</title></channel></rss>").encode("ISO-8859-1")
        http_headers = {"content-type": "text/xml; charset=ISO-8859-1"}
        result = {}
        converted = feedparsing.convert_to_utf8(http_headers, rss, result)
        self.assertTrue(title.encode("utf-8") in converted)
        self.assertEqual("ISO-8859-1", result["encoding"])

    def test_parse_content_type_header_matches_cgi(self):
        # Expected values taken from `cgi.parse_header` on Python 3.12:
        # cgi.parse_header("TEXT/XML; charset=UTF-8") == ("TEXT/XML", {"charset": "UTF-8"})
        # cgi.parse_header("xml") == ("xml", {})
        self.assertEqual(("TEXT/XML", {"charset": "UTF-8"}), _parse_content_type_header("TEXT/XML; charset=UTF-8"))
        self.assertEqual(("xml", {}), _parse_content_type_header("xml"))

    def test_atoma_parsing(self):
        from deluge_yarss2 import atoma

        atoma.rss.supported_rss_versions = []
        filename = "ettv-rss-1.xml"
        file_path = common.get_resource(filename, path="tests/data/feeds/")
        parsed_feeds = atoma.parse_rss_file(file_path)

        self.assertEqual("The top100 torrents", parsed_feeds.description)
        self.assertEqual("https://therss.so", parsed_feeds.link)
        self.assertEqual(None, parsed_feeds.ttl)
