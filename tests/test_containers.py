from pathlib import Path
import tests
from e4s_cl.cf.containers import (
    BackendUnsupported,
    BoundFile,
    Container,
    FileOptions,
    optimize_bind_addition,
)


class ContainerTest(tests.TestCase):

    def test_create(self):
        container = Container(name='dummy')
        self.assertFalse(type(container) == Container)
        self.assertTrue(isinstance(container, Container))

    def test_backend_unknown(self):
        with self.assertRaises(BackendUnsupported):
            container = Container(name='UNKNOWN')

    def test_bind_file(self):
        container = Container(name='dummy')

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

    def test_bind_file_inclusion(self):
        pmi = BoundFile(Path('/usr/lib/libpmi.so'), Path('/usr/lib/libpmi.so'),
                        FileOptions.READ_ONLY)
        mpi = BoundFile(Path('/usr/lib/libmpi.so'), Path('/usr/lib/libmpi.so'),
                        FileOptions.READ_ONLY)
        mpi_translated = BoundFile(Path('/usr/lib/libmpi.so'),
                                   Path('/.e4s-cl/hostlibs/libmpi.so'),
                                   FileOptions.READ_ONLY)
        usr = BoundFile(Path('/usr'), Path('/usr'), FileOptions.READ_ONLY)

        external_lib = BoundFile(Path('/opt/openmpi/lib'),
                                 Path('/usr/openmpi'), FileOptions.READ_ONLY)

        bound = {mpi, mpi_translated}

        self.assertSetEqual(optimize_bind_addition(pmi, bound), {pmi} | bound)
        self.assertSetEqual(optimize_bind_addition(mpi, bound), bound)
        self.assertSetEqual(optimize_bind_addition(usr, bound),
                            {usr, mpi_translated})

        self.assertSetEqual(optimize_bind_addition(mpi, {usr}), {usr})
        self.assertSetEqual(optimize_bind_addition(mpi_translated, {usr}),
                            {mpi_translated, usr})

        self.assertSetEqual(optimize_bind_addition(external_lib, {usr}),
                            {external_lib, usr})

    def test_bind_relative(self):
        container = Container(name='dummy')

        target = Path('/tmp/../proc/meminfo')

        ref = Path('/tmp')
        file = Path('/proc/meminfo')

        container.bind_file(target)
        files = set(map(lambda x: x.origin, container.bound))

        self.assertSetEqual({ref, file}, files)

    def test_double_bind(self):
        container = Container(name='dummy')

        library = Path(tests.ASSETS, 'libgver.so.0')
        library_symlink = Path(tests.ASSETS, 'libgver.so.0.0.0')
        target = Path('/', 'hostlibs', 'libgver.so.0')

        bind1 = BoundFile(library, target)
        bind2 = BoundFile(library_symlink, target)

        self.assertSetEqual({bind1}, optimize_bind_addition(bind2, {bind1}))
        self.assertSetEqual({bind2}, optimize_bind_addition(bind1, {bind2}))
