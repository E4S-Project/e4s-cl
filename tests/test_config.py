"""Test functions.

Functions used for unit tests of help.py.
"""

import tests
import shlex
from unittest.mock import patch
from io import StringIO
import e4s_cl.config
from e4s_cl.variables import set_dry_run
from pathlib import Path
from e4s_cl.cli.commands.launch import configuration_options
from e4s_cl.cli.commands.launch import COMMAND as launch_command
from e4s_cl.cf.containers import Container

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

    @patch('sys.stdout', new_callable = StringIO)
    def test_configured_launch(self, stdout):
        set_dry_run(True)
        launch_command.main(shlex.split(f"--backend containerless --image None mpirun hostname"))
        self.assertIn('-n 8', stdout.getvalue())

    def test_configured_sing_container(self):
        container = Container(name='singularity')
        command = ['']
        self.assertIn('diffname', container._prepare(command))
