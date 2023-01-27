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
  options: ['--volumepath', '/tmp']
""")


class ContainerTestPodman(tests.TestCase):

    def test_additional_options_config(self):
        container = Container(name='podman')
        command = ['']
        self.assertNotIn('--volumepath', container._prepare(command))
        config.update_configuration(TEST_CONFIGURATION)
        self.assertIn('--volumepath', container._prepare(command))
        self.assertIn('/tmp', container._prepare(command))
        config.update_configuration(DEFAULT_CONFIGURATION)
        self.assertNotIn('--volumepath', container._prepare(command))

    def test_additional_options_environment(self):
        container = Container(name='podman')
        command = ['']
        self.assertNotIn('--volumepath', container._prepare(command))
        environ['PODMAN_OPTIONS'] = "--volumepath /tmp"
        self.assertIn('--volumepath', container._prepare(command))
        self.assertIn('/tmp', container._prepare(command))
        del environ['PODMAN_OPTIONS']
        self.assertNotIn('--volumepath', container._prepare(command))
