import tests
from pathlib import Path
from sotools import Library, libraryset, linker
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
        lib_set = libraryset.LibrarySet.create_from(["libmpi.so"])

        self.assertTrue(lib_set.glib)

        filtered = filter_libraries(lib_set, None, None)

        self.assertFalse(filtered.glib)

    @tests.skipIf(not linker.resolve("libmpi.so"), "No test library available")
    def test_overlay_libraries(self):
        entry = Entrypoint()
        container = Container(name="containerless")
        lib_set = libraryset.LibrarySet.create_from(
            [linker.resolve("libmpi.so")])

        overlain = overlay_libraries(lib_set, container, entry)

        self.assertEqual(lib_set, overlain)

        self.assertEqual(
            Path(entry.linker).name,
            Path(lib_set.linkers.pop().binary_path).name)

    @tests.skipIf(not linker.resolve("libmpi.so"), "No test library available")
    def test_select_import_method(self):
        entry = Entrypoint()
        container = Container(name="containerless")
        lib_set = libraryset.LibrarySet.create_from(
            [linker.resolve("libmpi.so")])

        self.assertTrue(select_libraries(lib_set, container, entry))

    @tests.skipIf(not linker.resolve("libmpi.so"), "No test library available")
    def test_execute(self):
        set_dry_run(True)

        self.assertCommandReturnValue(0, COMMAND, [
            '--backend', 'containerless', '--image', '', '--libraries',
            linker.resolve('libmpi.so')
        ])
