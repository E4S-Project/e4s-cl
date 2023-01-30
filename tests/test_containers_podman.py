from os import getcwd, environ
from unittest import skipIf
from pathlib import Path
import tests
from e4s_cl.util import which
from e4s_cl.cf.containers import (
    BackendUnsupported,
    BoundFile,
    Container,
    FileOptions,
)

from e4s_cl import config

DEFAULT_CONFIGURATION = config.CONFIGURATION
TEST_CONFIGURATION = config.Configuration.create_from_string("""
podman:
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

        environ['PODMAN_OPTIONS'] = '--root /opt/podman'
        environ['PODMAN_RUN_OPTIONS'] = '--tz UTC+8'
        podman_command = container._prepare(command)
        self.assertContainsInOrder([
            '--root',
            '/opt/podman',
            'run',
            '--tz',
            'UTC+8',
        ], podman_command)

        del environ['PODMAN_OPTIONS']
        del environ['PODMAN_RUN_OPTIONS']
        podman_command = container._prepare(command)
        for option in {'--root', '/opt/podman', '--tz', 'UTC+8'}:
            self.assertNotIn(option, podman_command)
