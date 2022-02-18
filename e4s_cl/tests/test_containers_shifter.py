from os import getenv, getcwd
from unittest import skipIf
from pathlib import Path
from e4s_cl import tests
from e4s_cl.util import which
from e4s_cl.cf.containers import Container, BackendUnsupported, FileOptions


class ContainerTestShifter(tests.TestCase):

    def shifter_check():
        return (not which('shifter') and (not Path('shifter').exists()))

    def test_create(self):
        container = Container(executable='shifter', image='test')
        self.assertFalse(type(container) == Container)
        self.assertTrue(isinstance(container, Container))

    @skipIf(shifter_check(), "Shifter absent from system")
    def test_run_backend(self):
        container = Container(executable='shifter')
        command = ['']
        container_cmd = container._prepare(command)
        self.assertIn('shifter', ' '.join(map(str, container_cmd)))

    def test_run_image(self):
        container = Container(executable='shifter', image='imagenametest')
        command = ['']
        container_cmd = container._prepare(command)
        self.assertIn('imagenametest', ' '.join(map(str, container_cmd)))

    def test_run_pwd(self):
        container = Container(executable='shifter')
        command = ['']
        container_cmd = container._prepare(command)
        pwd = getcwd()
        self.assertIn(pwd, ' '.join(map(str, container_cmd)))

    def test_run_mpirun(self):
        container = Container(executable='shifter', image='dummyimagename')
        command = ['mpirun -n 2 ls']
        container_cmd = container._prepare(command)
        self.assertIn(command[0], ' '.join(map(str, container_cmd)))

    def test_bind_file(self):
        container = Container(executable='shifter')

        target = Path('/tmp')
        dest = Path('/tmp')
        option = FileOptions.READ_WRITE

        container.bind_file(target)
        self.assertIn((target, target, FileOptions.READ_ONLY),
                      list(container.bound))

        container.bind_file(target, dest=dest)
        self.assertIn((target, dest, FileOptions.READ_ONLY),
                      list(container.bound))

        container.bind_file(target, dest=dest, option=option)
        self.assertIn((target, dest, FileOptions.READ_WRITE),
                      list(container.bound))

    def test_bind_relative(self):
        container = Container(executable='shifter')

        target = Path('/tmp/../proc/meminfo')

        ref = Path('/tmp')
        file = Path('/proc/meminfo')

        container.bind_file(target)
        files = set(map(lambda x: x[0], container.bound))

        self.assertSetEqual({ref, file}, files)
