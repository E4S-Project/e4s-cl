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

CONFIG_EXECUTABLE = tests.ASSETS / 'bin' / 'podman-conf'
DEFAULT_CONFIGURATION = config.CONFIGURATION
TEST_CONFIGURATION = config.Configuration.create_from_string(f"""
backends:
  podman:
    executable: '{CONFIG_EXECUTABLE}'
    options: ['--root', '/opt/podman']
    run_options: ['--tz', 'UTC+8']
""")


class ContainerTestPodman(tests.TestCase):

    def test_additional_options_config(self):
        container = Container(name='podman')
        command = ['']

        podman_command = container._prepare(command)
        for option in {'--root', '/opt/podman', '--tz', 'UTC+8'}:
            self.assertNotIn(option, podman_command)

        config.update_configuration(TEST_CONFIGURATION)
        podman_command = container._prepare(command)
        self.assertContainsInOrder([
            '--root',
            '/opt/podman',
            'run',
            '--tz',
            'UTC+8',
        ], podman_command)

        config.update_configuration(DEFAULT_CONFIGURATION)
        podman_command = container._prepare(command)
        for option in {'--root', '/opt/podman', '--tz', 'UTC+8'}:
            self.assertNotIn(option, podman_command)

    def test_additional_options_environment(self):
        container = Container(name='podman')
        command = ['']

        podman_command = container._prepare(command)
        for option in {'--root', '/opt/podman', '--tz', 'UTC+8'}:
            self.assertNotIn(option, podman_command)

        environ['E4S_CL_PODMAN_OPTIONS'] = '--root /opt/podman'
        environ['E4S_CL_PODMAN_RUN_OPTIONS'] = '--tz UTC+8'
        podman_command = container._prepare(command)
        self.assertContainsInOrder([
            '--root',
            '/opt/podman',
            'run',
            '--tz',
            'UTC+8',
        ], podman_command)

        del environ['E4S_CL_PODMAN_OPTIONS']
        del environ['E4S_CL_PODMAN_RUN_OPTIONS']
        podman_command = container._prepare(command)
        for option in {'--root', '/opt/podman', '--tz', 'UTC+8'}:
            self.assertNotIn(option, podman_command)

    def test_executable(self):
        """Assert the default podman executable comes from $PATH"""
        container = Container(name='podman')

        default_path = environ.get('PATH', '')
        environ['PATH'] = f"{tests.ASSETS / 'bin'}{pathsep}{default_path}"

        self.assertEqual(tests.ASSETS / 'bin' / 'podman',
                         container._executable())

        environ['PATH'] = default_path

    def test_executable_config(self):
        """Assert the podman executable is read from the configuration"""
        container = Container(name='podman')

        config.update_configuration(TEST_CONFIGURATION)
        self.assertEqual(tests.ASSETS / 'bin' / 'podman-conf',
                         container._executable())

        config.update_configuration(DEFAULT_CONFIGURATION)

    def test_executable_env(self):
        """Assert the podman executable is read from the environment"""
        container = Container(name='podman')

        environ['E4S_CL_PODMAN_EXECUTABLE'] = str(tests.ASSETS / 'bin' /
                                                  'podman-env')
        self.assertEqual(tests.ASSETS / 'bin' / 'podman-env',
                         container._executable())

        del environ['E4S_CL_PODMAN_EXECUTABLE']

    def test_executable_priority(self):
        """Assert the environment has precedence over config and config over default"""
        container = Container(name='podman')

        default_path = environ.get('PATH', '')
        environ['PATH'] = f"{tests.ASSETS / 'bin'}{pathsep}{default_path}"
        config.update_configuration(TEST_CONFIGURATION)
        environ['E4S_CL_PODMAN_EXECUTABLE'] = str(tests.ASSETS / 'bin' /
                                                  'podman-env')

        self.assertEqual(tests.ASSETS / 'bin' / 'podman-env',
                         container._executable())

        del environ['E4S_CL_PODMAN_EXECUTABLE']

        self.assertEqual(tests.ASSETS / 'bin' / 'podman-conf',
                         container._executable())

        config.update_configuration(DEFAULT_CONFIGURATION)

        self.assertEqual(tests.ASSETS / 'bin' / 'podman',
                         container._executable())

        environ['PATH'] = default_path
