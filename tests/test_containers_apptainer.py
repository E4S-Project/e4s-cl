from os import getcwd, environ
import tests
from e4s_cl import config
from e4s_cl.cf.containers import (
    BackendUnsupported,
    BoundFile,
    Container,
    FileOptions,
)

DEFAULT_CONFIGURATION = config.CONFIGURATION
TEST_CONFIGURATION = config.Configuration.create_from_string("""
apptainer:
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

        environ['APPTAINER_OPTIONS'] = "--nocolor -s"
        environ['APPTAINER_EXEC_OPTIONS'] = "--hostname XxmycoolcontainerxX"
        apptainer_command = container._prepare(command)
        self.assertContainsInOrder([
            '--nocolor',
            '-s',
            'exec',
            '--hostname',
            'XxmycoolcontainerxX',
        ], apptainer_command)

        del environ['APPTAINER_OPTIONS']
        del environ['APPTAINER_EXEC_OPTIONS']
        apptainer_command = container._prepare(command)
        for option in {'--nocolor', '-s', '--hostname', 'XxmycoolcontainerxX'}:
            self.assertNotIn(option, apptainer_command)
