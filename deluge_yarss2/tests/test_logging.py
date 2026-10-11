#
# This file is part of YaRSS2 and is licensed under GNU General Public License 3.0, or later, with
# the additional special exception to link portions of this program with the OpenSSL library.
# See LICENSE for more details.
#

from unittest import mock

from twisted.internet import threads
from twisted.python import threadable
from twisted.trial import unittest

from deluge_yarss2.util import logging


class LoggerTestCase(unittest.TestCase):
    def test_gtkui_log_message_event_emitted_on_io_thread_from_worker_thread(self):
        # The reactor registers its thread only once it runs, which trial does not do
        self.addCleanup(setattr, threadable, "ioThread", threadable.ioThread)
        threadable.registerAsIOThread()

        emit_in_io_thread = []
        event_manager = mock.Mock()
        event_manager.emit.side_effect = lambda event: emit_in_io_thread.append(threadable.isInIOThread())
        logger = logging.getLogger(__name__)

        def verify_emitted_on_io_thread(result):
            self.assertEqual(emit_in_io_thread, [True])

        patcher = mock.patch.object(logging.component, "get", return_value=event_manager)
        patcher.start()
        self.addCleanup(patcher.stop)

        d = threads.deferToThread(logger.info, "Message from a worker thread")
        return d.addCallback(verify_emitted_on_io_thread)
