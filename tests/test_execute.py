import tests
from pathlib import Path
from sotools import Library, linker
from sotools.libraryset import LibrarySet
from e4s_cl.util import which
from e4s_cl.variables import set_dry_run
from e4s_cl.cf.template import Entrypoint
from e4s_cl.cf.containers import Container, FileOptions
import tempfile
from unittest.mock import patch
from e4s_cl.cli.commands.__execute import (import_library, filter_libraries,
                                           overlay_libraries, select_libraries,
                                           _filter_available_libraries,
                                           COMMAND)


class ExecuteTests(tests.TestCase):

    def test_filter_available_libraries_skips_unresolved_dependencies(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            ok_lib = Path(temp_dir) / 'libok.so'
            bad_lib = Path(temp_dir) / 'libbad.so'
            ok_lib.touch()
            bad_lib.touch()

            with patch(
                    'e4s_cl.cli.commands.__execute._missing_ldd_dependencies',
                    side_effect=[[], ['libhsa-runtime64.so.1']]):
                filtered = _filter_available_libraries([ok_lib, bad_lib])

            self.assertEqual(filtered, [ok_lib])

    def test_filter_available_libraries_skips_missing_paths(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            ok_lib = Path(temp_dir) / 'libok.so'
            missing_lib = Path(temp_dir) / 'libmissing.so'
            ok_lib.touch()

            with patch(
                    'e4s_cl.cli.commands.__execute._missing_ldd_dependencies',
                    return_value=[]):
                filtered = _filter_available_libraries([ok_lib, missing_lib])

            self.assertEqual(filtered, [ok_lib])

    def test_filter_available_libraries_ldd_fail_open(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            ok_lib = Path(temp_dir) / 'libok.so'
            ok_lib.touch()

            with patch(
                    'subprocess.run',
                    side_effect=OSError('ldd unavailable')):
                missing = _filter_available_libraries([ok_lib])

            self.assertEqual(missing, [ok_lib])

    @tests.skipIf(not linker.resolve("libmpi.so"), "No test library available")
    def test_lib_import(self):
        container = Container(name="containerless")

        lib = Library.from_path(linker.resolve("libmpi.so"))

        import_library(lib, container)

        links = set()
        for bound in container.bound:
            if bound.origin.resolve() == Path(lib.binary_path).resolve():
                links.add(bound.origin)

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
        lib_set = LibrarySet(host_libraries | host_bash)

        overlain = overlay_libraries(lib_set, container, entry)

        self.assertTrue(lib_set.intersection(overlain))

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

        libmpi = str(linker.resolve('libmpi.so'))

        self.assertCommandReturnValue(0, COMMAND, [
            '--backend',
            'containerless',
            '--image',
            '',
            '--libraries',
            libmpi,
            '--files',
            Path.home().as_posix(),
            'ls',
        ])

        set_dry_run(False)

        self.assertCommandReturnValue(0, COMMAND, [
            '--backend',
            'containerless',
            '--image',
            '',
            '--libraries',
            libmpi,
            'ls',
        ])

        self.assertCommandReturnValue(123, COMMAND, [
            '--backend',
            'containerless',
            '--image',
            '',
            '--libraries',
            libmpi,
            'bash',
            '-c',
            '"exit 123"',
        ])

    @tests.skipIf(not linker.resolve("libmpi.so"), "No test library available")
    def test_execute_alias(self):
        set_dry_run(True)

        libmpi = str(linker.resolve('libmpi.so'))

        with patch('e4s_cl.cf.containers.Container.bind_file') as bind_mock:
            with tempfile.NamedTemporaryFile() as temp_file:
                self.assertCommandReturnValue(0, COMMAND, [
                    '--backend',
                    'containerless',
                    '--image',
                    '',
                    '--libraries',
                    libmpi,
                    '--files',
                    f"{temp_file.name}:/tmp/target",
                    'ls',
                ])

                bind_mock.assert_any_call(temp_file.name, dest='/tmp/target', option=FileOptions.READ_WRITE)

        set_dry_run(False)

    @tests.skipIf(not linker.resolve("libmpi.so"), "No test library available")
    def test_execute_backend_args(self):
        set_dry_run(True)

        libmpi = str(linker.resolve('libmpi.so'))

        with patch('e4s_cl.cli.commands.__execute.Container.add_runtime_options') as add_opts:
            self.assertCommandReturnValue(0, COMMAND, [
                '--backend',
                'containerless',
                '--image',
                '',
                '--backend-args',
                '--fakeroot --cleanenv',
                '--libraries',
                libmpi,
                'ls',
            ])

            add_opts.assert_called_once_with(['--fakeroot', '--cleanenv'])

        set_dry_run(False)
