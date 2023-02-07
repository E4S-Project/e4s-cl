from os import getcwd, environ, pathsep
from unittest import skipIf
from pathlib import Path
import tests
from e4s_cl import config
from e4s_cl.util import which
from e4s_cl.cf.containers import (
    BackendUnsupported,
    BoundFile,
    Container,
    FileOptions,
)

CONFIG_EXECUTABLE = tests.ASSETS / 'bin' / 'singularity-conf'
DEFAULT_CONFIGURATION = config.CONFIGURATION
TEST_CONFIGURATION = config.Configuration.create_from_string(f"""
backends:
  singularity:
    executable: '{CONFIG_EXECUTABLE}'
    options: ['--nocolor', '-s']
    exec_options: ['--hostname', 'XxmycoolcontainerxX']
""")


class ContainerTestSingularity(tests.TestCase):

    def test_create(self):
        container = Container(name='singularity', image='test')
        self.assertFalse(type(container) == Container)
        self.assertTrue(isinstance(container, Container))

    def test_run_image(self):
        container = Container(name='singularity', image='imagenametest')
        command = ['']
        container_cmd = container._prepare(command)
        self.assertIn('imagenametest', ' '.join(map(str, container_cmd)))

    def test_run_pwd(self):
        container = Container(name='singularity')
        command = ['']
        container_cmd = container._prepare(command)
        pwd = getcwd()
        self.assertIn(pwd, ' '.join(map(str, container_cmd)))

    def test_run_mpirun(self):
        container = Container(name='singularity', image='dummyimagename')
        command = ['mpirun -n 2 ls']
        container_cmd = container._prepare(command)
        self.assertIn(command[0], ' '.join(map(str, container_cmd)))

    def test_bind_file(self):
        container = Container(name='singularity')

        target = Path('/tmp')
        dest = Path('/etc')
        contained_dest = Path("/etc/skel")
        option = FileOptions.READ_WRITE

        container.bind_file(target)
        self.assertIn(BoundFile(target, target, FileOptions.READ_ONLY),
                      list(container.bound))

        container._Container__bound_files = {}

        container.bind_file(target, dest=dest)
        self.assertIn(BoundFile(target, dest, FileOptions.READ_ONLY),
                      list(container.bound))

        container._Container__bound_files = {}

        container.bind_file(target, dest=dest)
        self.assertIn(BoundFile(target, dest, FileOptions.READ_ONLY),
                      list(container.bound))

        container.bind_file(target, dest=dest, option=option)
        self.assertIn(BoundFile(target, dest, FileOptions.READ_WRITE),
                      list(container.bound))

        container._Container__bound_files = {}

        container.bind_file(target, dest=contained_dest)
        self.assertIn(BoundFile(target, contained_dest, FileOptions.READ_ONLY),
                      list(container.bound))

        container.bind_file(target, dest=dest, option=option)
        self.assertIn(BoundFile(target, dest, FileOptions.READ_WRITE),
                      list(container.bound))

    def test_bind_relative(self):
        container = Container(name='singularity')

        target = Path('/tmp/../proc/meminfo')

        ref = Path('/tmp')
        file = Path('/proc/meminfo')
        home = Path.home()

        container.bind_file(target)
        files = set(map(lambda x: x.origin, container.bound))

        self.assertSetEqual({ref, file, home}, files)

    def test_additional_options_config(self):
        container = Container(name='singularity')
        command = ['']

        singularity_command = container._prepare(command)
        for option in {'--nocolor', '-s', '--hostname', 'XxmycoolcontainerxX'}:
            self.assertNotIn(option, singularity_command)

        config.update_configuration(TEST_CONFIGURATION)
        singularity_command = container._prepare(command)
        self.assertContainsInOrder([
            '--nocolor',
            '-s',
            'exec',
            '--hostname',
            'XxmycoolcontainerxX',
        ], singularity_command)

        config.update_configuration(DEFAULT_CONFIGURATION)
        singularity_command = container._prepare(command)
        for option in {'--nocolor', '-s', '--hostname', 'XxmycoolcontainerxX'}:
            self.assertNotIn(option, singularity_command)

    def test_additional_options_environment(self):
        container = Container(name='singularity')
        command = ['']

        singularity_command = container._prepare(command)
        for option in {'--nocolor', '-s', '--hostname', 'XxmycoolcontainerxX'}:
            self.assertNotIn(option, singularity_command)

        environ['E4S_CL_SINGULARITY_OPTIONS'] = "--nocolor -s"
        environ[
            'E4S_CL_SINGULARITY_EXEC_OPTIONS'] = "--hostname XxmycoolcontainerxX"
        singularity_command = container._prepare(command)
        self.assertContainsInOrder([
            '--nocolor',
            '-s',
            'exec',
            '--hostname',
            'XxmycoolcontainerxX',
        ], singularity_command)

        del environ['E4S_CL_SINGULARITY_OPTIONS']
        del environ['E4S_CL_SINGULARITY_EXEC_OPTIONS']
        singularity_command = container._prepare(command)
        for option in {'--nocolor', '-s', '--hostname', 'XxmycoolcontainerxX'}:
            self.assertNotIn(option, singularity_command)

    def test_executable(self):
        """Assert the default singularity executable comes from $PATH"""
        container = Container(name='singularity')

        default_path = environ.get('PATH', '')
        environ['PATH'] = f"{tests.ASSETS / 'bin'}{pathsep}{default_path}"

        self.assertEqual(tests.ASSETS / 'bin' / 'singularity',
                         container._executable())

        environ['PATH'] = default_path

    def test_executable_config(self):
        """Assert the singularity executable is read from the configuration"""
        container = Container(name='singularity')

        config.update_configuration(TEST_CONFIGURATION)
        self.assertEqual(tests.ASSETS / 'bin' / 'singularity-conf',
                         container._executable())

        config.update_configuration(DEFAULT_CONFIGURATION)

    def test_executable_env(self):
        """Assert the singularity executable is read from the environment"""
        container = Container(name='singularity')

        environ['E4S_CL_SINGULARITY_EXECUTABLE'] = str(tests.ASSETS / 'bin' /
                                                       'singularity-env')
        self.assertEqual(tests.ASSETS / 'bin' / 'singularity-env',
                         container._executable())

        del environ['E4S_CL_SINGULARITY_EXECUTABLE']

    def test_executable_priority(self):
        """Assert the environment has precedence over config and config over default"""
        container = Container(name='singularity')

        default_path = environ.get('PATH', '')
        environ['PATH'] = f"{tests.ASSETS / 'bin'}{pathsep}{default_path}"
        config.update_configuration(TEST_CONFIGURATION)
        environ['E4S_CL_SINGULARITY_EXECUTABLE'] = str(tests.ASSETS / 'bin' /
                                                       'singularity-env')

        self.assertEqual(tests.ASSETS / 'bin' / 'singularity-env',
                         container._executable())

        del environ['E4S_CL_SINGULARITY_EXECUTABLE']

        self.assertEqual(tests.ASSETS / 'bin' / 'singularity-conf',
                         container._executable())

        config.update_configuration(DEFAULT_CONFIGURATION)

        self.assertEqual(tests.ASSETS / 'bin' / 'singularity',
                         container._executable())

        environ['PATH'] = default_path

        # This fails as the which wrapper holds a cache
        #self.assertNotEqual(tests.ASSETS / 'bin' / 'singularity', container._executable())
