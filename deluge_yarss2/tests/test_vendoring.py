import json
import subprocess
import sys

from twisted.trial import unittest

import deluge_yarss2.atoma.utils


class VendoringTestCase(unittest.TestCase):
    def test_plugin_does_not_modify_sys_path(self):
        # A fresh interpreter, since the test process may have imported the plugin already.
        code = (
            "import json, sys\n"
            "from unittest import mock\n"
            "before = list(sys.path)\n"
            "import deluge_yarss2\n"
            "with mock.patch('deluge.plugins.init.PluginInitBase.__init__', return_value=None):\n"
            "    deluge_yarss2.CorePlugin('YaRSS2')\n"
            "from deluge_yarss2 import rssfeed_handling\n"
            "from deluge_yarss2.util import common\n"
            "path = common.get_resource('t1.rss', path='tests/data/feeds')\n"
            "parsed = rssfeed_handling.fetch_and_parse_rssfeed_atom(path)\n"
            "print(json.dumps([before, sys.path, len(parsed['items'])]))\n"
        )
        output = subprocess.check_output([sys.executable, "-c", code])
        before, after, item_count = json.loads(output.decode().splitlines()[-1])
        self.assertEqual(after, before)
        self.assertTrue(item_count > 0)

    def test_atoma_uses_vendored_dateutil(self):
        self.assertTrue(deluge_yarss2.atoma.utils.dateutil.__name__.startswith("deluge_yarss2._vendor"))
