from e4s_cl import tests
from e4s_cl.cli.commands.launch import COMMAND


class LaunchTest(tests.TestCase):
    def test_missing_arguments(self):
        argv = ['naive', '-n', '2', 'ls']
        self.assertNotCommandReturnValue(0, COMMAND, argv)
        argv = ['--backend', 'bash', 'naive', '-n', '2', 'ls']
        self.assertNotCommandReturnValue(0, COMMAND, argv)
        argv = ['--image', '/dev/null', 'naive', '-n', '2', 'ls']
        self.assertNotCommandReturnValue(0, COMMAND, argv)
