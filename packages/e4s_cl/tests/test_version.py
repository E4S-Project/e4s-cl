import pathlib
from e4s_cl import tests, E4S_CL_SCRIPT
from e4s_cl.cli.commands.__main__ import COMMAND as main


class VersionTest(tests.TestCase):
    def test_output(self):
        argv = ['-V']
        stdout, stderr = self.assertCommandReturnValue(0, main, argv)
