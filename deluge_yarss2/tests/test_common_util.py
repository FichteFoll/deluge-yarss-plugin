import json
import os
import subprocess
import sys
import zipfile
from pathlib import Path

from twisted.trial import unittest

import deluge_yarss2
from deluge_yarss2.util import common


# Plain pytest functions run inside the reactor greenlet of pytest-twisted,
# which leaves the reactor unusable for the trial test cases collected after them.
class CommonUtilTestCase(unittest.TestCase):
    def test_get_version(self):
        self.assertEqual(common.get_version(), deluge_yarss2.__version__)

    def test_get_resource_data_file(self):
        path = common.get_resource("yarss2.js")
        self.assertTrue(os.path.isfile(path))
        self.assertTrue(path.endswith(os.path.join("data", "yarss2.js")))

    def test_get_resource_test_data_file(self):
        path = common.get_resource("t1.rss", path="tests/data/feeds")
        self.assertTrue(os.path.isfile(path))

    def test_get_resource_from_zip(self):
        # Stock Deluge may import the plugin from a zipped egg.
        package_dir = Path(deluge_yarss2.__file__).parent
        tmp_dir = Path(self.mktemp()).absolute()
        tmp_dir.mkdir()
        zip_path = tmp_dir / "plugin.zip"
        with zipfile.ZipFile(zip_path, "w") as zf:
            for file in package_dir.rglob("*"):
                if file.is_file() and "__pycache__" not in file.parts:
                    zf.write(file, file.relative_to(package_dir.parent))
        code = (
            "import json, os, sys\n"
            "sys.path.insert(0, sys.argv[1])\n"
            "import deluge_yarss2\n"
            "from deluge_yarss2.util import common\n"
            "first = common.get_resource('yarss2.js')\n"
            "second = common.get_resource('yarss2.js')\n"
            "print(json.dumps([deluge_yarss2.__file__, first, os.path.isfile(first), second]))\n"
        )
        output = subprocess.check_output([sys.executable, "-c", code, str(zip_path)], cwd=tmp_dir)
        module_file, first, first_exists, second = json.loads(output.decode().splitlines()[-1])
        self.assertTrue(module_file.startswith(str(zip_path)), module_file)
        self.assertTrue(first.endswith(os.path.join("data", "yarss2.js")), first)
        self.assertTrue(first_exists)
        self.assertEqual(first, second)

    def test_isodate_to_datetime_unparsable_date_logs_warning(self):
        with self.assertLogs("deluge_yarss2.util.common", "WARNING") as cm:
            result = common.isodate_to_datetime("not a date")
        self.assertEqual(result, common.get_default_date())
        self.assertIn("isodate_to_datetime error", cm.output[0])
        self.assertIn("Unknown string format", cm.output[0])
