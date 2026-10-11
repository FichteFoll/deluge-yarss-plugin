#
# Copyright (C) 2012-2019 bendikro bro.devel+yarss2@gmail.com
#
# This file is part of YaRSS2 and is licensed under GNU General Public License 3.0, or later, with
# the additional special exception to link portions of this program with the OpenSSL library.
# See LICENSE for more details.
#
from unittest import mock

import pytest
from twisted.internet import defer, task
from twisted.trial import unittest

import deluge.component as component
import deluge.config
from deluge.ui.client import client

import deluge_yarss2.gtk3ui.gtkui
from deluge_yarss2.gtk3ui.gtkui import GtkUI
from deluge_yarss2.tests import common as tests_common
from deluge_yarss2.util import logging
from deluge_yarss2.yarss_config import default_prefs, get_fresh_email_config

from . import test_gtkui
from .utils.log_utils import plugin_tests_logger_name

deluge_yarss2.gtk3ui.gtkui.component = test_gtkui


class DummyComponent:
    def add_page(self, name, widget):
        pass

    def register_hook(self, name, func):
        pass


def get(string):
    return DummyComponent()


class GtkUITestCase(unittest.TestCase):
    def setUp(self):  # NOQA
        defer.setDebugging(True)
        tests_common.set_tmp_config_dir()
        client.start_standalone()

        self.log = logging.getLogger(plugin_tests_logger_name)
        self.gtkui = GtkUI("YaRSS2")
        self.gtkui.create_ui()

    def tearDown(self):  # NOQA
        client._daemon_proxy = None
        client.__started_standalone = False

        def on_shutdown(result):
            component._ComponentRegistry.components = {}

        return component.shutdown().addCallback(on_shutdown)


@pytest.mark.gui
class GtkUIGeneralSettingsTestCase(unittest.TestCase):
    def setUp(self):  # NOQA
        # Setting the config in the widgets triggers their signal handlers, which save to the core
        for method in ("save_general_config", "save_email_config"):
            patcher = mock.patch.object(GtkUI, method)
            setattr(self, method, patcher.start())
            self.addCleanup(patcher.stop)
        self.gtkui = GtkUI("YaRSS2")
        self.gtkui.create_ui()

    def tearDown(self):  # NOQA
        return component.deregister(self.gtkui)

    def build_config(self, max_concurrent_feeds=None):
        config = default_prefs()
        config["email_configurations"] = get_fresh_email_config()
        if max_concurrent_feeds is not None:
            config["general"]["max_concurrent_feeds"] = max_concurrent_feeds
        return config

    def test_update_data_from_config_sets_spinbutton(self):
        self.gtkui.update_data_from_config(self.build_config(max_concurrent_feeds=3))

        spinbutton = self.gtkui.glade.get_object("spinbutton_max_concurrent_feeds")
        self.assertEqual(3, spinbutton.get_value_as_int())

    def test_update_data_from_config_defaults_to_one(self):
        self.gtkui.update_data_from_config(self.build_config())

        spinbutton = self.gtkui.glade.get_object("spinbutton_max_concurrent_feeds")
        self.assertEqual(1, spinbutton.get_value_as_int())

    def test_save_configuration_data_saves_spinbutton_value(self):
        self.gtkui.update_data_from_config(self.build_config(max_concurrent_feeds=3))

        spinbutton = self.gtkui.glade.get_object("spinbutton_max_concurrent_feeds")
        spinbutton.set_value(5)

        self.gtkui.save_configuration_data()

        saved_config = self.save_general_config.call_args.args[0]
        self.assertEqual(5, saved_config["max_concurrent_feeds"])


@pytest.mark.label
class GtkUIWithCoreTestCase(unittest.TestCase):
    @defer.inlineCallbacks
    def setUp(self):  # NOQA
        # Must override callLater to avoid unclean twisted reactor
        clock = task.Clock()
        deluge.config.callLater = clock.callLater

        tests_common.set_tmp_config_dir()
        client.start_standalone()

        success = yield client.core.enable_plugin("Label")
        self.assertTrue(success, msg="Failed to enable Label plugin")

        self.log = logging.getLogger(plugin_tests_logger_name)
        self.gtkui = GtkUI("YaRSS2")
        self.gtkui.create_ui()

    def tearDown(self):  # NOQA
        client._daemon_proxy = None
        client.__started_standalone = False
        return component.shutdown()

    @defer.inlineCallbacks
    def test_get_labels(self, *patched_get):
        from deluge.i18n import setup_mock_translation

        setup_mock_translation()

        yield component.start()  # Necessary to avoid 'Reactor was unclean' error

        labels = yield self.gtkui.plugins_enabled_changed("Label")
        self.assertEqual([""], labels)

        # Add some labels
        client.label.add("Test-label")
        client.label.add("Test-label2")

        labels = yield self.gtkui.plugins_enabled_changed("Label")

        self.failUnlessIn("test-label", labels)
        self.failUnlessIn("test-label2", labels)
