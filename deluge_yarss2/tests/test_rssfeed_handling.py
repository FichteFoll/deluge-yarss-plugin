#
# Copyright (C) 2012-2019 bendikro bro.devel+yarss2@gmail.com
#
# This file is part of YaRSS2 and is licensed under GNU General Public License 3.0, or later, with
# the additional special exception to link portions of this program with the OpenSSL library.
# See LICENSE for more details.
#
import datetime
from unittest import mock
from urllib.error import URLError

import rencode
from twisted.trial import unittest

from deluge.error import DelugeError

import deluge_yarss2.util.common
from deluge_yarss2 import rssfeed_handling
from deluge_yarss2.util import common, logging

from . import common as test_common
from .base import TestCaseDebug
from .utils import assert_equal
from .utils.log_utils import plugin_tests_logger_name

log = logging.getLogger(plugin_tests_logger_name)


class RSSFeedHandlingTestCase(unittest.TestCase, TestCaseDebug):
    def setUp(self):  # NOQA
        self.log = log
        self.rssfeedhandler = rssfeed_handling.RSSFeedHandler(self.log)
        self.set_unittest_maxdiff(None)

    def test_handle_ttl_missing_value_is_treated_as_no_ttl(self):
        rssfeed_data = {"obey_ttl": True, "name": "x", "update_interval": 60}
        fetch_data = {}
        self.rssfeedhandler.handle_ttl(rssfeed_data, {"ttl": None}, fetch_data)
        self.assertNotIn("ttl", fetch_data)
        self.assertFalse(rssfeed_data["obey_ttl"])

    def test_get_rssfeed_parsed(self):
        file_url = deluge_yarss2.util.common.get_resource(test_common.testdata_rssfeed_filename, path="tests/")
        rssfeed_data = {
            "name": "Test",
            "url": file_url,
            "site:": "only used whith cookie arguments",
            "prefer_magnet": False,
        }
        site_cookies = {"uid": "18463", "passkey": "b830f87d023037f9393749s932"}
        user_agent = "User_agent_test"
        parsed_feed = self.rssfeedhandler.get_rssfeed_parsed(
            rssfeed_data, site_cookies_dict=site_cookies, user_agent=user_agent
        )

        # When needing to dump the result in json format
        # common.json_dump(parsed_feed["items"], "freebsd_rss_items_dump2.json")

        self.assertTrue("items" in parsed_feed)
        items = parsed_feed["items"]
        stored_items = test_common.load_json_testdata()

        assert_equal(items, stored_items)
        self.assertEqual(
            sorted(parsed_feed["cookie_header"]["Cookie"].split("; ")),
            ["passkey=b830f87d023037f9393749s932", "uid=18463"],
        )
        self.assertEqual(parsed_feed["user_agent"], user_agent)

    def test_get_rssfeed_showrss(self):
        filename = "showrss.xml"
        file_url = deluge_yarss2.util.common.get_resource(filename, path="tests/data/feeds")
        rssfeed_data = {
            "name": "Test",
            "url": file_url,
            "site:": "only used whith cookie arguments",
            "prefer_magnet": True,
        }
        parsed_feed = self.rssfeedhandler.get_rssfeed_parsed(rssfeed_data)

        # When needing to dump the result in json format
        # common.json_dump(parsed_feed["items"], "freebsd_rss_items_dump2.json")

        self.assertTrue("items" in parsed_feed)
        items = parsed_feed["items"]

        stored_items = {
            0: {
                "title": "The Show WEB H264 MEMENTO",
                "link": "magnet:?xt=urn:btih:AB3C1AD2258201BFD289D886F1062761D8427A40&dn=The+Show+WEB+H264+MEMENTO&tr=udp%3A%2F%2Ftracker.coppersurfer.tk%3A6969%2Fannounce&tr=udp%3A%2F%2Ftracker.leechers-paradise.org%3A6969%2Fannounce&tr=udp%3A%2F%2Ftracker.opentrackr.org%3A1337%2Fannounce&tr=http%3A%2F%2Ftracker.trackerfix.com%3A80%2Fannounce",  # noqa: E501
                "matches": False,
                "updated": "2019-10-14T03:10:26+00:00",
                "magnet": "magnet:?xt=urn:btih:AB3C1AD2258201BFD289D886F1062761D8427A40&dn=The+Show+WEB+H264+MEMENTO&tr=udp%3A%2F%2Ftracker.coppersurfer.tk%3A6969%2Fannounce&tr=udp%3A%2F%2Ftracker.leechers-paradise.org%3A6969%2Fannounce&tr=udp%3A%2F%2Ftracker.opentrackr.org%3A1337%2Fannounce&tr=http%3A%2F%2Ftracker.trackerfix.com%3A80%2Fannounce",  # noqa: E501
                "torrent": None,
            }
        }
        self.assertEqual(stored_items, items)

    def test_get_rssfeed_parsed_prefer_magnet_link(self):
        filename = "ezrss-rss-2.xml"
        file_url = deluge_yarss2.util.common.get_resource(filename, path="tests/data/feeds")

        rssfeed_data = {
            "name": "Test",
            "url": file_url,
            "site:": "only used whith cookie arguments",
            "prefer_magnet": True,
        }
        site_cookies = {"uid": "18463", "passkey": "b830f87d023037f9393749s932"}
        user_agent = "User_agent_test"
        parsed_feed = self.rssfeedhandler.get_rssfeed_parsed(
            rssfeed_data, site_cookies_dict=site_cookies, user_agent=user_agent
        )

        # When needing to dump the result in json format
        # common.json_dump(parsed_feed["items"], "freebsd_rss_items_dump2.json")

        self.assertTrue("items" in parsed_feed)
        items = parsed_feed["items"]

        stored_items = {
            0: {
                "title": "Lolly Tang 2009 09 26 WEB x264-TBS",
                "link": "magnet:?xt=urn:btih:4CF874831F61F5DB9C3299E503E28A8103047BA0&dn=Lolly.Tang.2009.09.26.WEB.x264-TBS%5Beztv%5D.mkv&tr=udp%3A%2F%2Ftracker.publicbt.com%2Fannounce&tr=udp%3A%2F%2Fopen.demonii.com%3A1337&tr=http%3A%2F%2Ftracker.trackerfix.com%3A80%2Fannounce&tr=udp%3A%2F%2Ftracker.coppersurfer.tk%3A6969&tr=udp%3A%2F%2Ftracker.leechers-paradise.org%3A6969&tr=udp%3A%2F%2Fexodus.desync.com%3A6969",  # noqa: E501
                "matches": False,
                "updated": "2019-09-27T08:12:48-04:00",
                "magnet": "magnet:?xt=urn:btih:4CF874831F61F5DB9C3299E503E28A8103047BA0&dn=Lolly.Tang.2009.09.26.WEB.x264-TBS%5Beztv%5D.mkv&tr=udp%3A%2F%2Ftracker.publicbt.com%2Fannounce&tr=udp%3A%2F%2Fopen.demonii.com%3A1337&tr=http%3A%2F%2Ftracker.trackerfix.com%3A80%2Fannounce&tr=udp%3A%2F%2Ftracker.coppersurfer.tk%3A6969&tr=udp%3A%2F%2Ftracker.leechers-paradise.org%3A6969&tr=udp%3A%2F%2Fexodus.desync.com%3A6969",  # noqa: E501
                "torrent": "https://zoink.ch/torrent/Lolly.Tang.2009.09.26.WEB.x264-TBS[eztv].mkv.torrent",
            },
            1: {
                "title": "The.Show.WEB.H264-MEMENTO",
                "link": "magnet:?xt=urn:btih:3B4BBDB57E3D83F900EA9844753006A7DA62D0B6&dn=The.Show.WEB.H264-MEMENTO[eztv].mkv&tr=udp%3A%2F%2Ftracker.publicbt.com%2Fannounce&tr=udp%3A%2F%2Fopen.demonii.com%3A1337&tr=http%3A%2F%2Ftracker.trackerfix.com%3A80%2Fannounce&tr=udp%3A%2F%2Ftracker.coppersurfer.tk%3A6969&tr=udp%3A%2F%2Ftracker.leechers-paradise.org%3A6969&tr=udp%3A%2F%2Fexodus.desync.com%3A6969",  # noqa: E501
                "matches": False,
                "updated": "2019-09-27T06:41:36-04:00",
                "magnet": "magnet:?xt=urn:btih:3B4BBDB57E3D83F900EA9844753006A7DA62D0B6&dn=The.Show.WEB.H264-MEMENTO[eztv].mkv&tr=udp%3A%2F%2Ftracker.publicbt.com%2Fannounce&tr=udp%3A%2F%2Fopen.demonii.com%3A1337&tr=http%3A%2F%2Ftracker.trackerfix.com%3A80%2Fannounce&tr=udp%3A%2F%2Ftracker.coppersurfer.tk%3A6969&tr=udp%3A%2F%2Ftracker.leechers-paradise.org%3A6969&tr=udp%3A%2F%2Fexodus.desync.com%3A6969",  # noqa: E501
                "torrent": "https://zoink.ch/torrent/The.Show.WEB.H264-MEMENTO[eztv].mkv.torrent",
            },
        }

        self.assertEqual(stored_items, items)
        self.assertEqual(
            ["passkey=b830f87d023037f9393749s932", "uid=18463"],
            sorted(parsed_feed["cookie_header"]["Cookie"].split("; ")),
        )
        self.assertEqual(user_agent, parsed_feed["user_agent"])

    def test_get_link(self):
        file_url = deluge_yarss2.util.common.get_resource(test_common.testdata_rssfeed_filename, path="tests/")
        parsed_feed = rssfeed_handling.fetch_and_parse_rssfeed(file_url)

        item = None
        for e in parsed_feed["items"]:
            item = e
            break

        # Item has enclosure, so it should use that link
        self.assertEqual(self.rssfeedhandler.get_link(item), item["enclosures"][0]["url"])

        # Remove enclosures
        item["enclosures"] = []
        # Item no longer has enclosures, so it should return the regular link
        self.assertEqual(self.rssfeedhandler.get_link(item), item["link"])

    def test_rssfeed_handling_fetch_xmlns_ezrss(self):
        from deluge_yarss2 import rssfeed_handling

        filename = "ettv-rss-3.xml"
        file_path = common.get_resource(filename, path="tests/data/feeds/")
        parsed_feeds = rssfeed_handling.fetch_and_parse_rssfeed(file_path)

        self.assertEqual(3, len(parsed_feeds["items"]))

        entry0 = parsed_feeds["items"][0]
        self.assertEqual("The.Show.WEB.H264-MEMENTO[ettv]", entry0["title"])
        magnet_link = (
            "magnet:?xt=urn:btih:CD44C326C5C4AC6EA08EAA5CDF61E53B1414BD05&dn=The.Show.WEB.H264-MEMENTO%5Bettv%5D"
        )
        magnet_uri = magnet_link.replace("&", "&amp;")

        self.assertEqual(magnet_link, entry0["link"])
        self.assertEqual("573162367", entry0["torrent"]["contentlength"])
        self.assertEqual("CD44C326C5C4AC6EA08EAA5CDF61E53B1414BD05", entry0["torrent"]["infohash"])
        self.assertEqual(magnet_uri, entry0["torrent"]["magneturi"])

    def test_rssfeed_handling_fetch_xmlns_ezrss_namespace(self):
        self.maxDiff = None
        from deluge_yarss2 import rssfeed_handling

        filename = "ezrss-rss-2.xml"

        file_path = common.get_resource(filename, path="tests/data/feeds/")
        parsed_feeds = rssfeed_handling.fetch_and_parse_rssfeed(file_path)

        self.assertEqual(2, len(parsed_feeds["items"]))

        entry0 = parsed_feeds["items"][0]
        self.assertEqual("Lolly Tang 2009 09 26 WEB x264-TBS", entry0["title"])
        link = "https://eztv.io/ep/1369854/lolly-tang-2009-09-26-web-x264-tbs/"
        self.assertEqual(link, entry0["link"])

        magnet_uri = "magnet:?xt=urn:btih:4CF874831F61F5DB9C3299E503E28A8103047BA0&dn=Lolly.Tang.2009.09.26.WEB.x264-TBS%5Beztv%5D.mkv&tr=udp%3A%2F%2Ftracker.publicbt.com%2Fannounce&tr=udp%3A%2F%2Fopen.demonii.com%3A1337&tr=http%3A%2F%2Ftracker.trackerfix.com%3A80%2Fannounce&tr=udp%3A%2F%2Ftracker.coppersurfer.tk%3A6969&tr=udp%3A%2F%2Ftracker.leechers-paradise.org%3A6969&tr=udp%3A%2F%2Fexodus.desync.com%3A6969"  # noqa: E501

        self.assertEqual("288475596", entry0["torrent"]["contentlength"])
        self.assertEqual("4CF874831F61F5DB9C3299E503E28A8103047BA0", entry0["torrent"]["infohash"])
        self.assertEqual(magnet_uri, entry0["torrent"]["magneturi"])

    def test_rssfeed_handling_fetch_with_enclosure(self):
        self.maxDiff = None
        from deluge_yarss2 import rssfeed_handling

        filename = "t1.rss"

        file_path = common.get_resource(filename, path="tests/data/feeds/")
        parsed_feeds = rssfeed_handling.fetch_and_parse_rssfeed(file_path)

        self.assertEqual(4, len(parsed_feeds["items"]))

        items = parsed_feeds["items"]
        item0 = items[0]
        item2 = items[2]

        link = "https://site.net/file.torrent"

        self.assertEqual("This is the title", item0["title"])
        self.assertEqual(link, rssfeed_handling.get_item_download_link(item0))
        self.assertEqual([(4541927915.52, "4.2 GiB")], rssfeed_handling.get_download_size(item0))

        self.assertEqual("[TORRENT] This is the title", item2["title"])
        self.assertEqual(link, rssfeed_handling.get_item_download_link(item2))
        self.assertEqual([857007476], rssfeed_handling.get_download_size(item2))

    def test_get_size(self):
        filename_or_url = deluge_yarss2.util.common.get_resource("t1.rss", path="tests/data/feeds/")
        parsed_feed = rssfeed_handling.fetch_and_parse_rssfeed(filename_or_url)

        size = self.rssfeedhandler.get_size(parsed_feed["items"][0])

        self.assertEqual(1, len(size))
        self.assertEqual((4541927915.52, "4.2 GiB"), size[0])

        size = self.rssfeedhandler.get_size(parsed_feed["items"][1])
        self.assertEqual(1, len(size))
        self.assertEqual((402349096.96, "383.7 MiB"), size[0])

        size = self.rssfeedhandler.get_size(parsed_feed["items"][2])
        self.assertEqual(1, len(size))
        self.assertEqual((857007476), size[0])

        size = self.rssfeedhandler.get_size(parsed_feed["items"][3])
        self.assertEqual(2, len(size))
        self.assertEqual((14353107637), size[0])
        self.assertEqual((13529146982.4, "12.6 GiB"), size[1])

    def test_parse_size(self):
        self.assertEqual((734003200.0, "700.0 MiB"), rssfeed_handling._parse_size("Size: 700 MiB"))
        self.assertEqual((1610612736.0, "1.5 GiB"), rssfeed_handling._parse_size("size: 1.5 gib"))
        self.assertEqual((2199023255552.0, "2.0 TiB"), rssfeed_handling._parse_size("Size: 2 TB"))
        self.assertEqual((524288.0, "512.0 KiB"), rssfeed_handling._parse_size("Size: 512 KB"))
        self.assertEqual((100.0, "100 B"), rssfeed_handling._parse_size("Size: 100 B"))
        self.assertEqual((0, None), rssfeed_handling._parse_size("No size here"))

    def get_default_rssfeeds_dict(self):
        match_option_dict = {}
        match_option_dict["regex_include"] = ""
        match_option_dict["regex_exclude"] = ""
        match_option_dict["regex_include_ignorecase"] = True
        match_option_dict["regex_exclude_ignorecase"] = True
        match_option_dict["custom_text_lines"] = None

        rssfeed_matching = {}
        rssfeed_matching["0"] = {"matches": False, "link": "", "title": "FreeBSD-9.0-RELEASE-amd64-all"}
        rssfeed_matching["1"] = {"matches": False, "link": "", "title": "FreeBSD-9.0-RELEASE-i386-all"}
        rssfeed_matching["2"] = {"matches": False, "link": "", "title": "fREEbsd-9.0-RELEASE-i386-all"}
        return match_option_dict, rssfeed_matching

    def test_update_rssfeeds_dict_matching(self):
        options, rssfeed_parsed = self.get_default_rssfeeds_dict()
        options["regex_include"] = "FreeBSD"
        matching, msg = self.rssfeedhandler.update_rssfeeds_dict_matching(rssfeed_parsed, options)
        self.assertEqual(len(matching.keys()), len(rssfeed_parsed.keys()))

        # Also make sure the items in 'matching' correspond to the matching items in rssfeed_parsed
        count = 0
        for key in rssfeed_parsed.keys():
            if rssfeed_parsed[key]["matches"]:
                self.assertTrue(key in matching, f"The matches dict does not contain the matching key '{key}'")
                count += 1
        self.assertEqual(
            count,
            len(matching.keys()),
            f"The number of items in matches dict ({count}) does not"
            f" match the number of matching items ({len(matching.keys())})",
        )

        # Try again with regex_include_ignorecase=False
        options["regex_include_ignorecase"] = False
        matching, msg = self.rssfeedhandler.update_rssfeeds_dict_matching(rssfeed_parsed, options)
        self.assertEqual(len(matching.keys()), len(rssfeed_parsed.keys()) - 1)

        options["regex_exclude"] = "i386"
        matching, msg = self.rssfeedhandler.update_rssfeeds_dict_matching(rssfeed_parsed, options)
        self.assertEqual(len(matching.keys()), len(rssfeed_parsed.keys()) - 2)

        # Fresh options
        options, rssfeed_parsed = self.get_default_rssfeeds_dict()

        # Custom line with unicode characters, norwegian ø and å, as well as Latin Small Letter Lambda with stroke
        options["custom_text_lines"] = ["Test line with æ and å, as well as ƛ"]
        options["regex_include"] = "æ"
        matching, msg = self.rssfeedhandler.update_rssfeeds_dict_matching(rssfeed_parsed, options)
        self.assertEqual(len(matching.keys()), 1)
        for key in matching.keys():
            self.assertEqual(matching[key]["title"], options["custom_text_lines"][0])
            self.assertEqual(matching[key]["regex_include_match"], (15, 17))

        options["regex_include"] = "with.*ƛ"
        matching, msg = self.rssfeedhandler.update_rssfeeds_dict_matching(rssfeed_parsed, options)
        self.assertEqual(len(matching.keys()), 1)
        for key in matching.keys():
            self.assertEqual(matching[key]["title"], options["custom_text_lines"][0])
            self.assertEqual(matching[key]["regex_include_match"], (10, 39))

        # Test exclude span
        options["regex_include"] = ".*"
        options["regex_exclude"] = "line.*å"
        matching, msg = self.rssfeedhandler.update_rssfeeds_dict_matching(rssfeed_parsed, options)
        for key in rssfeed_parsed.keys():
            if not rssfeed_parsed[key]["matches"]:
                self.assertEqual(rssfeed_parsed[key]["title"], options["custom_text_lines"][0])
                self.assertEqual(rssfeed_parsed[key]["regex_exclude_match"], (5, 24))
                break

    def test_fetch_feed_torrents(self):
        config = test_common.get_test_config_dict()
        matche_result = self.rssfeedhandler.fetch_feed_torrents(config, "0")  # 0 is the rssfeed key
        matches = matche_result["matching_torrents"]
        self.assertTrue(len(matches) == 3)

    def test_fetch_feed_torrents_custom_user_agent(self):
        config = test_common.get_test_config_dict()
        custom_user_agent = "TEST AGENT"
        config["rssfeeds"]["0"]["user_agent"] = custom_user_agent
        matche_result = self.rssfeedhandler.fetch_feed_torrents(config, "0")  # 0 is the rssfeed key
        self.assertEqual(matche_result["user_agent"], custom_user_agent)

    def test_feedparser_dates(self):
        file_url = deluge_yarss2.util.common.get_resource("rss_with_special_dates.rss", path="tests/data/feeds/")
        rssfeed_data = {"name": "Test", "url": file_url}
        parsed_feed = self.rssfeedhandler.get_rssfeed_parsed(rssfeed_data)

        for k, item in parsed_feed["items"].items():
            expected_item = {
                "title": "[TORRENT] Chicago.Fire.S02E18.720p.WEB-DL.DD5.1.H.264-KiNGS [PublicHD]",
                "link": "http://publichd.se/download.php?id=d8004c7344c8952177845891be9f9d3a2b92fd7d&f=Chicago.Fire.S02E18.720p.WEB-DL.DD5.1.H.264-KiNGS-[PublicHD]",  # noqa: E501
                "matches": False,
                "updated": "2014-10-04T03:44:14+00:00",
                "magnet": "magnet:?xt=urn:btih:3AAEY42EZCKSC54ELCI35H45HIVZF7L5&dn=Chicago.Fire.S02E18.720p.WEB-DL.DD5.1.H.264-KiNGS+[PublicHD]&tr=udp://tracker.publichd.eu/announce&tr=udp://tracker.1337x.org:80/announce&tr=udp://tracker.openbittorrent.com:80/announce&tr=http://fr33dom.h33t.com:3310/announce",  # noqa: E501
                "torrent": "http://publichd.se/download.php?id=d8004c7344c8952177845891be9f9d3a2b92fd7d&f=Chicago.Fire.S02E18.720p.WEB-DL.DD5.1.H.264-KiNGS-[PublicHD]",  # noqa: E501
            }
            self.assertEqual(expected_item, item)

            # Some RSS feeds do not have a proper timestamp
            if "updated_datetime" in item:
                updated_datetime = item["updated_datetime"]
                test_val = datetime.datetime(2014, 10, 4, 3, 44, 14)
                test_val = deluge_yarss2.util.common.datetime_add_timezone(test_val)
                self.assertEqual(test_val, updated_datetime)
                break

    def test_get_rssfeed_parsed_no_items(self):
        file_url = deluge_yarss2.util.common.get_resource("feed_no_items_issue15.rss", path="tests/data/feeds/")
        rssfeed_data = {"name": "Test", "url": file_url}
        parsed_feed = self.rssfeedhandler.get_rssfeed_parsed(rssfeed_data)
        self.assertTrue("items" not in parsed_feed)

    def test_get_rssfeed_parsed_datetime_no_timezone(self):
        file_url = deluge_yarss2.util.common.get_resource(
            "rss_datetime_parse_no_timezone.rss", path="tests/data/feeds/"
        )
        rssfeed_data = {"name": "Test", "url": file_url}
        parsed_feed = self.rssfeedhandler.get_rssfeed_parsed(rssfeed_data)
        self.assertTrue("items" in parsed_feed)

    def test_fetch_and_parse_rssfeed_atom_malformed_values(self):
        rss = b"""<?xml version="1.0"?>
<rss version="2.0"><channel>
<title>Feed</title><link>http://example.org</link><description>Feed</description>
<ttl>abc</ttl>
<image><url>http://example.org/i.png</url><title>Feed</title><link>http://example.org</link><width>abc</width></image>
<item><title>Item</title><link>http://example.org/1.torrent</link><pubDate>2020-01-01T00:00:00+25:00</pubDate></item>
</channel></rss>"""
        parsed_feed = rssfeed_handling.fetch_and_parse_rssfeed_atom(rss)
        self.assertIsNone(parsed_feed["feed"]["ttl"])
        self.assertEqual(["Item"], [item["title"] for item in parsed_feed["items"]])
        self.assertNotIn("published_date", parsed_feed["items"][0])

    def test_get_rssfeed_parsed_server_error_message(self):
        file_url = deluge_yarss2.util.common.get_resource(
            "rarbg.to.rss.too_many_requests.html", path="tests/data/feeds/"
        )
        rssfeed_data = {"name": "Test", "url": file_url}
        parsed_feed = self.rssfeedhandler.get_rssfeed_parsed(rssfeed_data)
        self.assertTrue("items" not in parsed_feed)
        self.assertTrue("too many requests" in parsed_feed["raw_result"]["raw_result"])

    def test_get_rssfeed_parsed_unparsable_result_is_rpc_encodable(self):
        file_url = deluge_yarss2.util.common.get_resource(
            "rarbg.to.rss.too_many_requests.html", path="tests/data/feeds/"
        )
        rssfeed_data = {"name": "Test", "url": file_url}
        parsed_feed = self.rssfeedhandler.get_rssfeed_parsed(rssfeed_data)
        rencode.dumps(parsed_feed)
        self.assertIsInstance(parsed_feed["bozo_exception"], str)

    def test_get_rssfeed_parsed_feed_without_channel_is_bozo(self):
        file_url = deluge_yarss2.util.common.get_resource("broken-no-channel.xml", path="tests/atoma/rss/")
        rssfeed_data = {"name": "Test", "url": file_url}
        parsed_feed = self.rssfeedhandler.get_rssfeed_parsed(rssfeed_data)
        self.assertIsInstance(parsed_feed["bozo_exception"], str)
        self.assertEqual(parsed_feed["raw_result"]["items"], [])

    def test_get_rssfeed_parsed_network_error(self):
        rssfeed_data = {"name": "Test", "url": "https://example.invalid/rss"}
        error = URLError(TimeoutError("The handshake operation timed out"))
        with mock.patch.object(rssfeed_handling, "fetch_and_parse_rssfeed", side_effect=error):
            with self.assertRaises(DelugeError) as context:
                self.rssfeedhandler.get_rssfeed_parsed(rssfeed_data)
        self.assertEqual(
            str(context.exception),
            "Failed to fetch RSS Feed 'Test' from 'https://example.invalid/rss': The handshake operation timed out",
        )

    # def test_test_feedparser_parse(self):
    #     #file_url = deluge_yarss2.util.common.get_resource(test_common.testdata_rssfeed_filename, path="tests/")
    #     from deluge_yarss2.lib.feedparser import feedparser
    #     file_url = ""
    #     parsed_feed = feedparser.parse(file_url, timeout=10)
    #     item = None
    #     for item in parsed_feed["items"]:
    #         print "item:", type(item)
    #         print "item:", item.keys()
    #         #break
    #     # Item has enclosure, so it should use that link
    #     #self.assertEquals(self.rssfeedhandler.get_link(item), item.enclosures[0]["href"])
    #     #del item["links"][:]
    #     # Item no longer has enclosures, so it should return the regular link
    #     #self.assertEquals(self.rssfeedhandler.get_link(item), item["link"])
    #
    # def test_test_get_rssfeed_parsed(self):
    #     #file_url = ""
    #     file_url = deluge_yarss2.util.common.get_resource("data/feeds/72020rarcategory_tv.xml", path="tests/")
    #     rssfeed_data = {"name": "Test", "url": file_url, "site:": "only used whith cookie arguments",
    #                     "user_agent": None, "prefer_magnet": True}
    #     site_cookies = {"uid": "18463", "passkey": "b830f87d023037f9393749s932"}
    #     default_user_agent = self.rssfeedhandler.user_agent
    #     parsed_feed = self.rssfeedhandler.get_rssfeed_parsed(rssfeed_data, site_cookies_dict=site_cookies)
    #     print "parsed_feed:", parsed_feed.keys()
    #     #print "items:", parsed_feed["items"]
    #     for i in parsed_feed["items"]:
    #         print parsed_feed["items"][i]
    #         break

    # def test_download_link_with_equal_sign(self):
    #     file_url = deluge_yarss2.util.common.get_resource("rss_with_equal_sign_in_link.rss", path="tests/data/")
    #     from deluge_yarss2.lib.feedparser import feedparser
    #     from deluge_yarss2.torrent_handling import TorrentHandler, TorrentDownload
    #     rssfeed_data = {"name": "Test", "url": file_url, "site:": "only used whith cookie arguments"}
    #     parsed_feed = self.rssfeedhandler.get_rssfeed_parsed(rssfeed_data, site_cookies_dict=None)
    #     print "parsed_feed:", parsed_feed["items"]


# Name:  FreeBSD-9.0-RELEASE-amd64-all
# Name:  FreeBSD-9.0-RELEASE-i386-all
# Name:  FreeBSD-9.0-RELEASE-ia64-all
# Name:  FreeBSD-9.0-RELEASE-powerpc-all
# Name:  FreeBSD-9.0-RELEASE-powerpc64-all
# Name:  FreeBSD-9.0-RELEASE-sparc64-all
# Name:  FreeBSD-9.0-RELEASE-amd64-bootonly
# Name:  FreeBSD-9.0-RELEASE-amd64-disc1
# Name:  FreeBSD-9.0-RELEASE-amd64-dvd1
# Name:  FreeBSD-9.0-RELEASE-amd64-memstick
# Name:  FreeBSD-9.0-RELEASE-i386-bootonly
# Name:  FreeBSD-9.0-RELEASE-i386-disc1
# Name:  FreeBSD-9.0-RELEASE-i386-dvd1
# Name:  FreeBSD-9.0-RELEASE-i386-memstick
# Name:  FreeBSD-9.0-RELEASE-ia64-bootonly
# Name:  FreeBSD-9.0-RELEASE-ia64-memstick
# Name:  FreeBSD-9.0-RELEASE-ia64-release
# Name:  FreeBSD-9.0-RELEASE-powerpc-bootonly
# Name:  FreeBSD-9.0-RELEASE-powerpc-memstick
# Name:  FreeBSD-9.0-RELEASE-powerpc-release
# Name:  FreeBSD-9.0-RELEASE-powerpc64-bootonly
# Name:  FreeBSD-9.0-RELEASE-powerpc64-memstick
# Name:  FreeBSD-9.0-RELEASE-powerpc64-release
# Name:  FreeBSD-9.0-RELEASE-sparc64-bootonly
# Name:  FreeBSD-9.0-RELEASE-sparc64-disc1
