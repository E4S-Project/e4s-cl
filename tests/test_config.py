"""
Assert basic configuration capabilities are supported
"""

import tests
import shlex
from io import StringIO
from pathlib import Path
from unittest.mock import patch
import e4s_cl.config
from e4s_cl.config import flatten, Configuration, ALLOWED_CONFIG, ConfigurationError
from e4s_cl.variables import set_dry_run
from e4s_cl.cf.containers import Container
from e4s_cl.cli.commands.launch import COMMAND as launch_command


class ConfigTest(tests.TestCase):
    """Unit tests for e4s-cl's configuration file use"""

    def test_flat(self):
        data = {
            'container_directory': '/diffdirectory',
            'launcher_options': '-n 8',
            'singularity': {
                'options': '--hostname diffname',
                'build_options': {
                    'location': '-s'
                }
            }
        }
        flat_data = {
            'container_directory': '/diffdirectory',
            'launcher_options': '-n 8',
            'singularity_options': '--hostname diffname',
            'singularity_build_options_location': '-s'
        }
        self.assertEqual(flatten(data), flat_data)

    def test_bad_type(self):
        data = """---
launcher_options: 8"""

        with self.assertRaises(ConfigurationError):
            config = Configuration.create_from_string(data)

    def test_merge(self):
        fields1 = {'a': 1, 'b': 3}
        fields2 = {'a': 5}
        fields3 = {'c': 0, 'd': 0, 'e': 0}
        c1, c2, c3 = Configuration(fields1), Configuration(
            fields2), Configuration(fields3)

        merged = c1 | c2 | c3
        expected = Configuration(dict(a=5, b=3, c=0, d=0, e=0))

        self.assertEqual(merged._fields, expected._fields)

    def test_completion(self):
        c = Configuration.default()

        for field in ALLOWED_CONFIG:
            self.assertEqual(getattr(c, field.key, None), field.default())

    def test_access(self):
        fields = {'a': 1, 'b': 2}
        c = Configuration(fields)
        self.assertEqual(getattr(c, 'a', None), 1)
        self.assertEqual(getattr(c, 'b', None), 2)
        self.assertIsNone(getattr(c, 'c', None))

    def test_assets(self):
        self.assertNotEqual(
            Configuration.create_from_file(tests.ASSETS / "e4s-cl.yaml"),
            Configuration.default())
