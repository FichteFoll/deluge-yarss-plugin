from importlib.metadata import entry_points

from twisted.trial import unittest

from deluge.plugins.init import PluginInitBase

from deluge_yarss2.core import Core
from deluge_yarss2.webui import WebUI


class PluginInitTestCase(unittest.TestCase):
    def setUp(self):  # NOQA
        self.patch(PluginInitBase, "__init__", lambda self, plugin_name: None)

    def _load_plugin_cls(self, group):
        (entry_point,) = entry_points(group=group, name="YaRSS2")
        plugin_cls = entry_point.load()
        return plugin_cls("YaRSS2")

    def test_core_entry_point(self):
        plugin = self._load_plugin_cls("deluge.plugin.core")
        self.assertIs(plugin._plugin_cls, Core)

    def test_web_entry_point(self):
        plugin = self._load_plugin_cls("deluge.plugin.web")
        self.assertIs(plugin._plugin_cls, WebUI)
