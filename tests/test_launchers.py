from shlex import split
import tests
from e4s_cl.cf.launchers import interpret


class LauncherTest(tests.TestCase):
    def test_standard(self):
        text = 'ls'
        launcher, command = interpret(split(text))

        self.assertFalse(launcher)
        self.assertEqual(command, ['ls'])

    def test_mpirun(self):
        text = 'mpirun -n 2 hostname'
        launcher, command = interpret(split(text))

        self.assertEqual(launcher[0], 'mpirun')
        self.assertEqual(command, ['hostname'])

    def test_unsupported(self):
        text = 'mylauncher -n 4 -p 2 command'
        launcher, command = interpret(split(text))

        self.assertFalse(launcher)
        self.assertEqual(command, split(text))

    def test_dashes(self):
        text = 'mpirun -n 2 -- hostname'
        launcher, command = interpret(split(text))

        self.assertEqual(launcher[0], 'mpirun')
        self.assertEqual(command, ['hostname'])

        text = 'mylauncher -n 4 -p 2 -- command'
        launcher, command = interpret(split(text))

        self.assertEqual(launcher[0], 'mylauncher')
        self.assertEqual(command, ['command'])
