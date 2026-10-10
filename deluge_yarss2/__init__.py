# -*- coding: utf-8 -*-
#
# Copyright (C) 2012-2015 bendikro bro.devel+yarss2@gmail.com
#
# Based on work by:
# Copyright (C) 2009 Camillo Dell'mour <cdellmour@gmail.com>
#
# Basic plugin template created by:
# Copyright (C) 2008 Martijn Voncken <mvoncken@gmail.com>
# Copyright (C) 2007-2009 Andrew Resch <andrewresch@gmail.com>
# Copyright (C) 2009 Damien Churchill <damoxc@gmail.com>
#
# This file is part of YaRSS2 and is licensed under GNU General Public License 3.0, or later, with
# the additional special exception to link portions of this program with the OpenSSL library.
# See LICENSE for more details.
#

import sys
from pathlib import Path

from deluge.plugins.init import PluginInitBase

from deluge_yarss2.util import logging

__version__ = "2.1.5"

log = logging.getLogger(__name__)


# Temporary until the vendored libraries are imported without sys.path changes.
VENDORED_LIB_DIRS = [
    "",
    "dateutil",
    "defusedxml",
    "beautifulsoup/py3k",
    "atoma",
    "html5lib",
    "webencodings",
]


def load_libs():
    include_dir = Path(__file__).parent / "include"
    for lib_dir in VENDORED_LIB_DIRS:
        location = str(include_dir / lib_dir)
        if location not in sys.path:
            sys.path.append(location)
        log.info("Appending to sys.path: '%s'" % location)


class CorePlugin(PluginInitBase):
    def __init__(self, plugin_name):
        load_libs()
        from .core import Core as CorePluginClass
        self._plugin_cls = CorePluginClass
        super(CorePlugin, self).__init__(plugin_name)


class Gtk3UIPlugin(PluginInitBase):
    def __init__(self, plugin_name):
        load_libs()
        from .gtk3ui.gtkui import GtkUI as GtkUIPluginClass
        self._plugin_cls = GtkUIPluginClass
        super(Gtk3UIPlugin, self).__init__(plugin_name)


class WebUIPlugin(PluginInitBase):
    def __init__(self, plugin_name):
        load_libs()
        from .webui import WebUI as WebUIPluginClass
        self._plugin_cls = WebUIPluginClass
        super(WebUIPlugin, self).__init__(plugin_name)
