import tests
from pathlib import Path
from sotools import Library, linker
from sotools.libraryset import LibrarySet
from e4s_cl.util import which
from e4s_cl.variables import set_dry_run
from e4s_cl.cf.template import Entrypoint
from e4s_cl.cf.containers import Container
from e4s_cl.cli.commands.__execute import (import_library, filter_libraries,
                                           overlay_libraries, select_libraries,
                                           COMMAND)


class ExecuteTests(tests.TestCase):

    @tests.skipIf(not linker.resolve("libmpi.so"), "No test library available")
    def test_lib_import(self):
        container = Container(name="containerless")

        lib = Library.from_path(linker.resolve("libmpi.so"))

        import_library(lib, container)

        links = set()
        for src, _, _ in container.bound:
            if src.resolve() == Path(lib.binary_path).resolve():
                links.add(src)

        self.assertGreater(len(links), 1)

    @tests.skipIf(not linker.resolve("libmpi.so"), "No test library available")
    def test_filter_libraries(self):
        lib_set = LibrarySet.create_from(["libmpi.so"])

        self.assertTrue(lib_set.glib)

        filtered = filter_libraries(lib_set, None, None)

        self.assertFalse(filtered.glib)

    @tests.skipIf(not linker.resolve("libmpi.so"), "No test library available")
    def test_overlay_libraries(self):
        entry = Entrypoint()
        container = Container(name="containerless")
        host_libraries = LibrarySet.create_from([linker.resolve("libmpi.so")])
        host_bash = LibrarySet.create_from([which('bash')])
        lib_set = LibrarySet(host_libraries.union(host_bash))

        overlain = overlay_libraries(lib_set, container, entry)

        self.assertEqual(lib_set, overlain)

        self.assertEqual(
            Path(entry.linker).name,
            Path(lib_set.linkers.pop().binary_path).name)

    @tests.skipIf(not linker.resolve("libmpi.so"), "No test library available")
    def test_select_import_method(self):
        entry = Entrypoint()
        container = Container(name="containerless")
        lib_set = LibrarySet.create_from([linker.resolve("libmpi.so")])

        self.assertTrue(select_libraries(lib_set, container, entry))

    @tests.skipIf(not linker.resolve("libmpi.so"), "No test library available")
    def test_execute(self):
        set_dry_run(True)

        self.assertCommandReturnValue(0, COMMAND, [
            '--backend', 'containerless', '--image', '', '--libraries',
            linker.resolve('libmpi.so'), '--files',
            Path.home().as_posix(), 'ls'
        ])

        set_dry_run(False)

        self.assertCommandReturnValue(0, COMMAND, [
            '--backend', 'containerless', '--image', '', '--libraries',
            linker.resolve('libmpi.so'), 'ls'
        ])

        self.assertCommandReturnValue(123, COMMAND, [
            '--backend', 'containerless', '--image', '', '--libraries',
            linker.resolve('libmpi.so'), 'bash', '-c', '"exit 123"'
        ])
