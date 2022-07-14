"""Test functions.

Functions used for unit tests of help.py.
"""

import tests
import shlex
from io import StringIO
from pathlib import Path
from unittest.mock import patch
import e4s_cl.config
from e4s_cl.variables import set_dry_run
from e4s_cl.cf.containers import Container
from e4s_cl.cli.commands.launch import COMMAND as launch_command

configuration_file = Path(Path(__file__).parent, "assets","e4s-cl.yaml").as_posix()
configuration = e4s_cl.config.Configuration(configuration_file)

class ConfigTest(tests.TestCase):
    """Unit tests for e4s-cl's configuration file use"""
    def test_container_dir(self):
        self.assertEqual(configuration.updated_globals.get('CONTAINER_DIR'), "/diffdirectory")

    def test_configuration_options(self):
        self.assertEqual(configuration.options('LAUNCHER_OPTIONS'), ['-n', '8'])
        self.assertEqual(configuration.options('SINGULARITY_OPTIONS', 'cli_options'), ['--hostname', 'diffname'])

        self.assertEqual(configuration.options(None), [])
        
        self.assertEqual(configuration.options('OPTION_NONE'), [])

    @patch('sys.stdout', new_callable = StringIO)
    def test_configured_launch(self, stdout):
        set_dry_run(True)
        launch_command.main(shlex.split(f"--backend containerless --image None mpirun hostname"))
        self.assertIn('-n 8', stdout.getvalue())

    def test_configured_sing_container(self):
        container = Container(name='singularity')
        command = ['']
        self.assertIn('diffname', container._prepare(command))
