import warnings

from twisted.internet import defer
from twisted.internet.defer import maybeDeferred
from twisted.trial import unittest

import deluge.component as component


class TestCaseDebug:

    def enable_twisted_debug(self):
        defer.setDebugging(True)
        import twisted.internet.base
        twisted.internet.base.DelayedCall.debug = True

    def set_unittest_maxdiff(self, value):
        self.maxDiff = value
        from .utils import assert_equal
        assert_equal.__self__.maxDiff = None


# Ported from deluge/tests/basetest.py at tag deluge-2.0.5,
# which Deluge removed in 2.1.0 and which PyPI wheels never shipped.
# This file is part of Deluge and is licensed under GNU General Public License 3.0, or later, with
# the additional special exception to link portions of this program with the OpenSSL library.
class BaseTestCase(unittest.TestCase):
    """This is the base class that should be used for all test classes
    that create classes that inherit from deluge.component.Component. It
    ensures that the component registry has been cleaned up when tests
    have finished.

    """

    def setUp(self):  # NOQA: N802
        if len(component._ComponentRegistry.components) != 0:
            warnings.warn(
                'The component._ComponentRegistry.components is not empty on test setup.\n'
                'This is probably caused by another test that did not clean up after finishing!: '
                f'{component._ComponentRegistry.components}'
            )
        d = maybeDeferred(self.set_up)

        def on_setup_error(error):
            warnings.warn(f'Error caught in test setup!\n{error.getTraceback()}')
            self.fail()

        return d.addErrback(on_setup_error)

    def tearDown(self):  # NOQA: N802
        d = maybeDeferred(self.tear_down)

        def on_teardown_failed(error):
            warnings.warn(f'Error caught in test teardown!\n{error.getTraceback()}')
            self.fail()

        def on_teardown_complete(result):
            component._ComponentRegistry.components.clear()
            component._ComponentRegistry.dependents.clear()

        return d.addCallbacks(on_teardown_complete, on_teardown_failed)

    def set_up(self):
        pass

    def tear_down(self):
        pass
