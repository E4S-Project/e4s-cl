from os import environ
import sys
from pathlib import Path
from importlib import import_module
from shlex import split
import tests
from e4s_cl import config
from e4s_cl.cf import launchers
from e4s_cl.cf.launchers import (
    Parser,
    filter_arguments,
    get_reserved_directories,
    interpret,
)

TEST_OPTIONS = ['--mca', 'btl_tcp_if_include', 'ib0']
DEFAULT_CONFIGURATION = config.CONFIGURATION
TEST_CONFIGURATION = config.Configuration.create_from_string(f"""
launcher_options: {TEST_OPTIONS}
""")


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

    def test_filter_arguments(self):
        """Check argument filtering support"""
        parser = Parser({'-a': 1, '-c': 2})
        command_line = "-a test -b 1 2 3 -c ofi btl -d host1:2,host2:2".split(
            ' ')

        valid, foreign = filter_arguments(parser, command_line)

        self.assertEqual(valid, "-a test -c ofi btl".split())
        self.assertEqual(foreign, "-b 1 2 3 -d host1:2,host2:2".split())

    def test_concat_arguments(self):
        """
        Check concatenated argument support
        """
        text = "srun -n4 -pgpu -Acourses01-gpu command"
        launcher, command = interpret(split(text))

        self.assertEqual(launcher, ['srun', '-n4', '-pgpu', '-Acourses01-gpu'])
        self.assertEqual(command, ['command'])

    def test_additional_options_config(self):
        """Check configuration options get added to the launcher command"""
        command = ['mpirun', '-np', '4', './foo', '--bar']

        launcher, application = interpret(command)
        self.assertEqual(launcher, ['mpirun', '-np', '4'])
        self.assertEqual(application, ['./foo', '--bar'])

        config.update_configuration(TEST_CONFIGURATION)
        launcher, application = interpret(command)
        self.assertEqual(launcher, ['mpirun', '-np', '4', *TEST_OPTIONS])
        self.assertEqual(application, ['./foo', '--bar'])

        config.update_configuration(DEFAULT_CONFIGURATION)
        launcher, application = interpret(command)
        self.assertEqual(launcher, ['mpirun', '-np', '4'])
        self.assertEqual(application, ['./foo', '--bar'])

    def test_additional_options_environment(self):
        """Check environment options get added to the launcher command"""
        command = ['mpirun', '-np', '4', './foo', '--bar']

        launcher, application = interpret(command)
        self.assertEqual(launcher, ['mpirun', '-np', '4'])
        self.assertEqual(application, ['./foo', '--bar'])

        environ['E4S_CL_LAUNCHER_OPTIONS'] = " ".join(TEST_OPTIONS)
        launcher, application = interpret(command)
        self.assertEqual(launcher, ['mpirun', '-np', '4', *TEST_OPTIONS])
        self.assertEqual(application, ['./foo', '--bar'])

        del environ['E4S_CL_LAUNCHER_OPTIONS']
        launcher, application = interpret(command)
        self.assertEqual(launcher, ['mpirun', '-np', '4'])
        self.assertEqual(application, ['./foo', '--bar'])

    def test_additional_options_priority(self):
        """Check environment options get precedence over configuration"""
        command = ['mpirun', '-np', '4', './foo', '--bar']

        launcher, application = interpret(command)
        self.assertEqual(launcher, ['mpirun', '-np', '4'])
        self.assertEqual(application, ['./foo', '--bar'])

        environ['E4S_CL_LAUNCHER_OPTIONS'] = " ".join([*TEST_OPTIONS, '--env'])
        config.update_configuration(TEST_CONFIGURATION)
        launcher, application = interpret(command)
        self.assertEqual(launcher,
                         ['mpirun', '-np', '4', *TEST_OPTIONS, '--env'])
        self.assertEqual(application, ['./foo', '--bar'])

        del environ['E4S_CL_LAUNCHER_OPTIONS']
        launcher, application = interpret(command)
        self.assertEqual(launcher, ['mpirun', '-np', '4', *TEST_OPTIONS])
        self.assertEqual(application, ['./foo', '--bar'])

        config.update_configuration(DEFAULT_CONFIGURATION)
        launcher, application = interpret(command)
        self.assertEqual(launcher, ['mpirun', '-np', '4'])
        self.assertEqual(application, ['./foo', '--bar'])
