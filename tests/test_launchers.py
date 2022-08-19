import sys
from pathlib import Path
from importlib import import_module
from shlex import split
import tests
from e4s_cl.cf import launchers
from e4s_cl.cf.launchers import interpret, get_reserved_directories


class LauncherTest(tests.TestCase):

    @classmethod
    def setUpClass(cls):
        tests.TestCase.setUpClass()
        test_module_name = 'assets.test_launcher_module'
        import_module(name=test_module_name)

        for script_name in sys.modules[test_module_name].SCRIPT_NAMES:
            launchers.LAUNCHERS.update({script_name: test_module_name})

    def test_no_launcher(self):
        """
        Check a command is not interpreted as a launcher
        """
        text = 'ls -alh /dev'
        launcher, command = interpret(split(text))

        self.assertFalse(launcher)
        self.assertEqual(command, split(text))

    def test_option(self):
        """
        Check option support
        """
        launcher_txt = 'mylauncher -a -b test'
        command_txt = 'command'
        cmd_line = split(launcher_txt) + split(command_txt)
        launcher, command = interpret(cmd_line)

        self.assertEqual(launcher, split(launcher_txt))
        self.assertEqual(command, split(command_txt))

    def test_unsupported_option(self):
        """
        Check unsupported option behaviour
        """
        launcher_txt = 'mylauncher -z 4'
        command_txt = 'command'
        cmd_line = split(launcher_txt) + split(command_txt)
        launcher, command = interpret(cmd_line)

        self.assertNotEqual(launcher, split(launcher_txt))
        self.assertNotEqual(command, split(command_txt))

    def test_equalled_option(self):
        """
        Check support for --x=y style options
        """
        launcher_txt = "mylauncher --option1=a --option2=a:b:c --option3='something or another'"
        command_txt = 'command'
        cmd_line = split(launcher_txt) + split(command_txt)
        launcher, command = interpret(cmd_line)

        self.assertEqual(launcher, split(launcher_txt))
        self.assertEqual(command, split(command_txt))

    def test_get_reserved_directories(self):
        """
        Check access of metadata
        """
        dirs = get_reserved_directories(['mylauncher'])

        self.assertEqual([Path('/reserved')], dirs)

    def test_dashes(self):
        """
        Check dashes separate commands properly
        """
        launcher_txt = 'mylauncher -n 2'
        command_txt = 'hostname'
        cmd_line = [*split(launcher_txt), '--', *split(command_txt)]
        launcher, command = interpret(cmd_line)

        self.assertEqual(launcher, split(launcher_txt))
        self.assertEqual(command, split(command_txt))

        launcher_txt = 'unsupported -z 4'
        command_txt = 'hostname'
        cmd_line = [*split(launcher_txt), '--', *split(command_txt)]
        launcher, command = interpret(cmd_line)

        self.assertEqual(launcher, split(launcher_txt))
        self.assertEqual(command, split(command_txt))

    def test_E_flag_split(self):
        """
        Check complex argument support
        """
        text = "mpirun -E 'two words' command"
        launcher, command = interpret(split(text))

        self.assertEqual(launcher, ['mpirun', '-E', 'two words'])
        self.assertEqual(command, ['command'])
