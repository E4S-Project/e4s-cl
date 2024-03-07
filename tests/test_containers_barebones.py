from os import getcwd, environ, pathsep
from unittest import skipIf
from pathlib import Path
import tests
from e4s_cl import config, BAREBONES_LIBRARY_DIR
from e4s_cl.util import which, list_directory_files
from e4s_cl.cf.containers import (
    BackendUnsupported,
    BoundFile,
    Container,
    FileOptions,
)

CONFIG_EXECUTABLE = tests.ASSETS / 'bin' / 'barebones-conf'
DEFAULT_CONFIGURATION = config.CONFIGURATION
TEST_CONFIGURATION = config.Configuration.create_from_string(f"""
backends:
  barebones:
    exec_options: ['--hostname', 'XxmycoolcontainerxX']
""")


class ContainerTestBarebones(tests.TestCase):

    def test_create(self):
        container = Container(name='barebones', image='None')
        self.assertFalse(type(container) == Container)
        self.assertTrue(isinstance(container, Container))

    def test_run_image(self):
        container = Container(name='barebones', image='imagenametest')
        command = ['']
        container_cmd = container._prepare(command)
        self.assertIn('imagenametest', ' '.join(map(str, container_cmd)))

    def test_run_pwd(self):
        container = Container(name='barebones')
        command = ['']
        container_cmd = container._prepare(command)
        pwd = getcwd()
        self.assertIn(pwd, ' '.join(map(str, container_cmd)))

    def test_run_mpirun(self):
        container = Container(name='barebones', image='dummyimagename')
        command = ['mpirun -n 2 ls']
        container_cmd = container._prepare(command)
        self.assertIn(command[0], ' '.join(map(str, container_cmd)))

    def test_bind_file(self):
        container = Container(name='barebones')

        target = Path('/tmp')
        dest = Path('/etc')
        contained_dest = Path("/etc/skel")
        option = FileOptions.READ_WRITE

        container.bind_file(target)
        self.assertIn('tmp',
                      [Path(path).name for path in list_directory_files(Path(BAREBONES_LIBRARY_DIR))])

        target = Path('/tmp2')
        dest = Path(BAREBONES_LIBRARY_DIR + str(target))
        container.bind_file(target, dest=dest)
        self.assertIn('tmp2',
                      [Path(path).name for path in list_directory_files(Path(BAREBONES_LIBRARY_DIR))])

    def test_bind_relative(self):
        container = Container(name='barebones')

        target = Path('/tmp/../proc/meminfo')

        ref = Path('/tmp')
        file_ex = Path('/proc/meminfo')
        home = Path.home()
        paths = {ref, file_ex, home}

        container.bind_file(target)
        files = set(map(lambda x: x.origin, container.bound))

        for item in paths:
            self.assertIn(item, files)

    def test_additional_options_config(self):
        container = Container(name='barebones')
        command = ['']

        barebones_command = container._prepare(command)
        for option in {'--nocolor', '-s', '--hostname', 'XxmycoolcontainerxX'}:
            self.assertNotIn(option, barebones_command)

        config.update_configuration(TEST_CONFIGURATION)
        barebones_command = container._prepare(command)
        self.assertContainsInOrder([
            '--nocolor',
            '-s',
            'exec',
            '--hostname',
            'XxmycoolcontainerxX',
        ], barebones_command)

        config.update_configuration(DEFAULT_CONFIGURATION)
        barebones_command = container._prepare(command)
        for option in {'--nocolor', '-s', '--hostname', 'XxmycoolcontainerxX'}:
            self.assertNotIn(option, barebones_command)

    def test_additional_options_environment(self):
        container = Container(name='barebones')
        command = ['']

        barebones_command = container._prepare(command)
        for option in {'--nocolor', '-s', '--hostname', 'XxmycoolcontainerxX'}:
            self.assertNotIn(option, barebones_command)

        environ['E4S_CL_barebones_OPTIONS'] = "--nocolor -s"
        environ[
            'E4S_CL_barebones_EXEC_OPTIONS'] = "--hostname XxmycoolcontainerxX"
        barebones_command = container._prepare(command)
        self.assertContainsInOrder([
            '--nocolor',
            '-s',
            'exec',
            '--hostname',
            'XxmycoolcontainerxX',
        ], barebones_command)

        del environ['E4S_CL_barebones_OPTIONS']
        del environ['E4S_CL_barebones_EXEC_OPTIONS']
        barebones_command = container._prepare(command)
        for option in {'--nocolor', '-s', '--hostname', 'XxmycoolcontainerxX'}:
            self.assertNotIn(option, barebones_command)
