from os import getcwd
from pathlib import Path
import tests
from e4s_cl import config
from e4s_cl.cf.containers import (
    BoundFile,
    Container,
    FileOptions,
)
from tests.test_containers_sif_like import SifLikeContainerTestMixin

CONFIG_EXECUTABLE = tests.ASSETS / 'bin' / 'singularity-conf'
DEFAULT_CONFIGURATION = config.CONFIGURATION
TEST_CONFIGURATION = config.Configuration.create_from_string(f"""
backends:
  singularity:
    executable: '{CONFIG_EXECUTABLE}'
    options: ['--nocolor', '-s']
    exec_options: ['--hostname', 'XxmycoolcontainerxX']
""")


class ContainerTestSingularity(tests.TestCase, SifLikeContainerTestMixin):

    BACKEND_NAME = 'singularity'
    ENV_PREFIX = 'SINGULARITY'
    CONFIG_EXECUTABLE = tests.ASSETS / 'bin' / 'singularity-conf'
    TEST_CONFIGURATION = TEST_CONFIGURATION
    DEFAULT_CONFIGURATION = DEFAULT_CONFIGURATION

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
        file_ex = Path('/proc/meminfo')
        home = Path.home()
        paths = {ref, file_ex, home}

        container.bind_file(target)
        files = set(map(lambda x: x.origin, container.bound))

        for item in paths:
            self.assertIn(item, files)

