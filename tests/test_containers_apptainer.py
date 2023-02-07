from os import getcwd, environ, pathsep
import tests
from e4s_cl import config
from e4s_cl.cf.containers import (
    BackendUnsupported,
    BoundFile,
    Container,
    FileOptions,
)

CONFIG_EXECUTABLE = tests.ASSETS / 'bin' / 'apptainer-conf'
DEFAULT_CONFIGURATION = config.CONFIGURATION
TEST_CONFIGURATION = config.Configuration.create_from_string(f"""
backends:
  apptainer:
    executable: '{CONFIG_EXECUTABLE}'
    options: ['--nocolor', '-s']
    exec_options: ['--hostname', 'XxmycoolcontainerxX']
""")


class ContainerTestApptainer(tests.TestCase):

    def test_additional_options_config(self):
        container = Container(name='apptainer')
        command = ['']

        apptainer_command = container._prepare(command)
        for option in {'--nocolor', '-s', '--hostname', 'XxmycoolcontainerxX'}:
            self.assertNotIn(option, apptainer_command)

        config.update_configuration(TEST_CONFIGURATION)
        apptainer_command = container._prepare(command)
        self.assertContainsInOrder([
            '--nocolor',
            '-s',
            'exec',
            '--hostname',
            'XxmycoolcontainerxX',
        ], apptainer_command)

        config.update_configuration(DEFAULT_CONFIGURATION)
        apptainer_command = container._prepare(command)
        for option in {'--nocolor', '-s', '--hostname', 'XxmycoolcontainerxX'}:
            self.assertNotIn(option, apptainer_command)

    def test_additional_options_environment(self):
        container = Container(name='apptainer')
        command = ['']

        apptainer_command = container._prepare(command)
        for option in {'--nocolor', '-s', '--hostname', 'XxmycoolcontainerxX'}:
            self.assertNotIn(option, apptainer_command)

        environ['E4S_CL_APPTAINER_OPTIONS'] = "--nocolor -s"
        environ[
            'E4S_CL_APPTAINER_EXEC_OPTIONS'] = "--hostname XxmycoolcontainerxX"
        apptainer_command = container._prepare(command)
        self.assertContainsInOrder([
            '--nocolor',
            '-s',
            'exec',
            '--hostname',
            'XxmycoolcontainerxX',
        ], apptainer_command)

        del environ['E4S_CL_APPTAINER_OPTIONS']
        del environ['E4S_CL_APPTAINER_EXEC_OPTIONS']
        apptainer_command = container._prepare(command)
        for option in {'--nocolor', '-s', '--hostname', 'XxmycoolcontainerxX'}:
            self.assertNotIn(option, apptainer_command)

    def test_executable(self):
        """Assert the default apptainer executable comes from $PATH"""
        container = Container(name='apptainer')

        default_path = environ.get('PATH', '')
        environ['PATH'] = f"{tests.ASSETS / 'bin'}{pathsep}{default_path}"

        self.assertEqual(tests.ASSETS / 'bin' / 'apptainer',
                         container._executable())

        environ['PATH'] = default_path

    def test_executable_config(self):
        """Assert the apptainer executable is read from the configuration"""
        container = Container(name='apptainer')

        config.update_configuration(TEST_CONFIGURATION)
        self.assertEqual(tests.ASSETS / 'bin' / 'apptainer-conf',
                         container._executable())

        config.update_configuration(DEFAULT_CONFIGURATION)

    def test_executable_env(self):
        """Assert the apptainer executable is read from the environment"""
        container = Container(name='apptainer')

        environ['E4S_CL_APPTAINER_EXECUTABLE'] = str(tests.ASSETS / 'bin' /
                                                     'apptainer-env')
        self.assertEqual(tests.ASSETS / 'bin' / 'apptainer-env',
                         container._executable())

        del environ['E4S_CL_APPTAINER_EXECUTABLE']

    def test_executable_priority(self):
        """Assert the environment has precedence over config and config over default"""
        container = Container(name='apptainer')

        default_path = environ.get('PATH', '')
        environ['PATH'] = f"{tests.ASSETS / 'bin'}{pathsep}{default_path}"
        config.update_configuration(TEST_CONFIGURATION)
        environ['E4S_CL_APPTAINER_EXECUTABLE'] = str(tests.ASSETS / 'bin' /
                                                     'apptainer-env')

        self.assertEqual(tests.ASSETS / 'bin' / 'apptainer-env',
                         container._executable())

        del environ['E4S_CL_APPTAINER_EXECUTABLE']

        self.assertEqual(tests.ASSETS / 'bin' / 'apptainer-conf',
                         container._executable())

        config.update_configuration(DEFAULT_CONFIGURATION)

        self.assertEqual(tests.ASSETS / 'bin' / 'apptainer',
                         container._executable())

        environ['PATH'] = default_path
