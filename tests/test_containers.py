from unittest import skipIf
from pathlib import Path
import tests
from e4s_cl.cf.containers import Container, BackendUnsupported, FileOptions


class ContainerTest(tests.TestCase):
    def test_create(self):
        container = Container(executable='bash')
        self.assertFalse(type(container) == Container)
        self.assertTrue(isinstance(container, Container))

    def test_backend_unknown(self):
        with self.assertRaises(BackendUnsupported):
            container = Container(executable='UNKNOWN')

    def test_bind_file(self):
        container = Container(executable='bash')

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
        container = Container(executable='bash')

        target = Path('/tmp/../proc/meminfo')

        ref = Path('/tmp')
        file = Path('/proc/meminfo')

        container.bind_file(target)
        files = set(map(lambda x: x[0], container.bound))

        self.assertSetEqual({ref, file}, files)
