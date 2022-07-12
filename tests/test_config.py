"""Test functions.

Functions used for unit tests of help.py.
"""

import tests
import e4s_cl.config
from pathlib import Path
from e4s_cl.cli.commands.launch import configuration_options

configuration_file = Path(Path(__file__).parent, "assets","e4s-cl.yaml").as_posix()
CONFIGURATION_VALUES = e4s_cl.config.Configuration(configuration_file).updated_globals

class ConfigTest(tests.TestCase):
    """Unit tests for e4s-cl's configuration file use"""
    def test_container_dir(self):
        self.assertEqual(CONFIGURATION_VALUES.get('CONTAINER_DIR'), "/diffdirectory")

    def test_configuration_options(self):
        self.assertEqual(configuration_options('LAUNCHER_OPTIONS', CONFIGURATION_VALUES), ['-n', '8'])
        self.assertEqual(configuration_options('CONTAINER_OPTIONS', CONFIGURATION_VALUES), ['--hostname', 'diffname'])

        self.assertEqual(configuration_options(None), [])
        
        self.assertEqual(configuration_options('OPTION_NONE'), [])
