import pathlib
import tests
from e4s_cl.cli.commands.__main__ import COMMAND as main


class VersionTest(tests.TestCase):
    def test_output(self):
        argv = ['-V']
        stdout, stderr = self.assertCommandReturnValue(0, main, argv)
