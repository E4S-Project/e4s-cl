from e4s_cl import tests
from e4s_cl.cli.commands.launch import COMMAND


class LaunchTest(tests.TestCase):
    def test_simple(self):
        argv = ['naive', '-n', '2', 'ls']
        self.assertCommandReturnValue(0, COMMAND, argv)
