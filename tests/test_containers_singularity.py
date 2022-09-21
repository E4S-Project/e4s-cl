from os import getenv, getcwd
from unittest import skipIf
from pathlib import Path
import tests
from e4s_cl.util import which
from e4s_cl.cf.containers import Container, BackendUnsupported, FileOptions

import e4s_cl.config as config

configuration_file = Path(Path(__file__).parent, "assets",
                          "e4s-cl.yaml").as_posix()
DEFAULT_CONFIGURATION = config.CONFIGURATION
TEST_CONFIGURATION = config.Configuration.create_from_file(configuration_file)


class ContainerTestSingularity(tests.TestCase):

    def singularity_check():
        return (not which('singularity')
                and (not Path('singularity').exists()))

    def test_create(self):
        container = Container(name='singularity', image='test')
        self.assertFalse(type(container) == Container)
        self.assertTrue(isinstance(container, Container))

    @skipIf(singularity_check(), "Singularity absent from system")
    def test_run_backend(self):
        container = Container(name='singularity')
        command = ['']
        container_cmd = container._prepare(command)
        self.assertIn('singularity', ' '.join(map(str, container_cmd)))

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
        option = FileOptions.READ_WRITE

        container.bind_file(target)
        self.assertIn((target, target, FileOptions.READ_ONLY),
                      list(container.bound))

        container._Container__bound_files = {}

        container.bind_file(target, dest=dest)
        self.assertIn((target, dest, FileOptions.READ_ONLY),
                      list(container.bound))

        container._Container__bound_files = {}

        container.bind_file(target, dest=dest)
        self.assertIn((target, dest, FileOptions.READ_ONLY),
                      list(container.bound))

        container.bind_file(target, dest=dest, option=option)
        self.assertIn((target, dest, FileOptions.READ_WRITE),
                      list(container.bound))

    def test_bind_relative(self):
        container = Container(name='singularity')

        target = Path('/tmp/../proc/meminfo')

        ref = Path('/tmp')
        file = Path('/proc/meminfo')
        home = Path.home()

        container.bind_file(target)
        files = set(map(lambda x: x[0], container.bound))

        self.assertSetEqual({ref, file, home}, files)

    def test_configured_container(self):
        container = Container(name='singularity')
        command = ['']
        config.update_configuration(TEST_CONFIGURATION)
        self.assertIn('diffname', container._prepare(command))
        config.update_configuration(DEFAULT_CONFIGURATION)
