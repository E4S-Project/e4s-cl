"""Test functions.

Functions used for unit tests of help.py.
"""

import tests
import shlex
from io import StringIO
from pathlib import Path
from unittest.mock import patch
import e4s_cl.config
from e4s_cl.config import flatten, Configuration
from e4s_cl.variables import set_dry_run
from e4s_cl.cf.containers import Container
from e4s_cl.cli.commands.launch import COMMAND as launch_command

configuration_file = Path(Path(__file__).parent, "assets",
                          "e4s-cl.yaml").as_posix()
configuration = e4s_cl.config.Configuration.create_from(configuration_file)


class ConfigTest(tests.TestCase):
    """Unit tests for e4s-cl's configuration file use"""

    def test_container_dir(self):
        self.assertEqual(configuration.container_directory, "/diffdirectory")

    def test_configuration_options(self):
        self.assertEqual(configuration.launcher_options, ['-n', '8'])
        self.assertEqual(configuration.singularity_cli_options,
                         ['--hostname', 'diffname'])

        self.assertEqual(configuration.none_options, [])

    @patch('sys.stdout', new_callable=StringIO)
    def test_configured_launch(self, stdout):
        set_dry_run(True)
        launch_command.main(
            shlex.split(
                f"--backend containerless --image None mpirun hostname"))
        self.assertIn('-n 8', stdout.getvalue())

    def test_configured_sing_container(self):
        container = Container(name='singularity')
        command = ['']
        self.assertIn('diffname', container._prepare(command))

    def test_flat(self):
        data = {
            'container directory': '/diffdirectory',
            'launcher options': '-n 8',
            'singularity': {
                'cli_options': '--hostname diffname',
                'build_options': {
                    'location': '-s'
                }
            }
        }
        flat_data = {
            'container directory': '/diffdirectory',
            'launcher options': '-n 8',
            'singularity_cli_options': '--hostname diffname',
            'singularity_build_options_location': '-s'
        }
        self.assertEqual(flatten(data), flat_data)

    def test_merge(self):
        fields1 = {'a': 1, 'b': 3}
        fields2 = {'a': 5}
        fields3 = {'c': 0, 'd': 0, 'e': 0}
        c1, c2, c3 = Configuration(fields1), Configuration(
            fields2), Configuration(fields3)

        merged = c1 | c2 | c3
        expected = Configuration(dict(a=5, b=3, c=0, d=0, e=0))

        self.assertEqual(merged._fields, expected._fields)
