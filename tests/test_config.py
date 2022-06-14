"""Test functions.

Functions used for unit tests of help.py.
"""

import tests
import e4s_cl.config
from pathlib import Path

configuration_file = Path(Path(__file__).parent, "assets","e4s-cl.yaml").as_posix()

class ConfigTest(tests.TestCase):
    """Unit tests for e4s-cl's configuration file use"""
    def test_config(self):
        CONFIGURATION_VALUES = e4s_cl.config.Configuration(configuration_file).updated_globals
        self.assertEqual(CONFIGURATION_VALUES.get('CONTAINER_DIR'), "/newdirectory")
