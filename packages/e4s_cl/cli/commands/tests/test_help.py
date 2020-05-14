"""Test functions.

Functions used for unit tests of help.py.
"""

from e4s_cl import tests
from e4s_cl.cli.commands.help import COMMAND as help_command


class HelpTest(tests.TestCase):
    """Unit tests for `taucmdr help`"""
    def test_help(self):
        argv = ['profile']
        self.assertCommandReturnValue(0, help_command, argv)

    def test_h_arg(self):
        stdout, _ = self.assertCommandReturnValue(0, help_command, ['-h'])
        self.assertIn('Show this help message and exit', stdout)

    def test_help_arg(self):
        stdout, _ = self.assertCommandReturnValue(0, help_command, ['--help'])
        self.assertIn('Show this help message and exit', stdout)
