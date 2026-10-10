from deluge.log import setup_logger

# Disables Deluge's new release check for all tests
from . import common as test_common  # noqa: F401
from .utils.log_utils import setup_tests_logging

setup_logger()

setup_tests_logging()
