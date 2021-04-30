import os
import pathlib
from unittest import skipIf
from e4s_cl import tests
from e4s_cl.util import which
from e4s_cl.cf.libraries import host_libraries, ldd, resolve, LibrarySet, Library, is_elf


class LibraryTest(tests.TestCase):
    def test_host_libraries(self):
        self.assertNotEqual(host_libraries(), {})

    @skipIf(not which('ls'), "No binary to test with")
    def test_ldd(self):
        ls_bin = which('ls')
        libraries = ldd(ls_bin)

        self.assertTrue({'libc.so.6', 'linker'} < set(libraries.keys()))

    @skipIf(not which('ls'), "No binary to test with")
    def test_resolving(self):
        """
        Check ldd output equals resolve output
        """
        ls_bin = which('ls')
        libraries = ldd(ls_bin)

        dependencies = set(libraries.keys())
        dependencies.difference_update({'linker'})

        for soname in dependencies:
            self.assertEqual(os.path.realpath(libraries[soname]['path']),
                             resolve(soname))

    @skipIf(not resolve('libm.so.6'), "No library to test with")
    def test_set(self):
        libset = LibrarySet()

        with open(resolve('libm.so.6'), 'rb') as file:
            libset.add(Library(file=file))

        self.assertEqual(len(libset), 1)
        self.assertSetEqual(libset.sonames, {'libm.so.6'})

    @skipIf(not resolve('libm.so.6'), "No library to test with")
    def test_set_resolve(self):
        libset = LibrarySet()

        with open(resolve('libm.so.6'), 'rb') as file:
            libset.add(Library(file=file))

        libset = libset.resolve()

        self.assertGreater(len(libset), 1)
        self.assertTrue(libset.sonames > {'libm.so.6', 'libc.so.6'})

    @skipIf(not resolve('libm.so.6'), "No library to test with")
    def test_set_missing(self):
        libset = LibrarySet()

        with open(resolve('libm.so.6'), 'rb') as file:
            libset.add(Library(file=file))

        self.assertIn('libc.so.6', libset.missing_libraries)

    @skipIf(not resolve('libm.so.6'), "No library to test with")
    def test_set_top(self):
        libset = LibrarySet()

        with open(resolve('libm.so.6'), 'rb') as file:
            libset.add(Library(file=file))

        self.assertIn('libm.so.6', libset.top_level.sonames)

    @skipIf(not resolve('libm.so.6'), "No library to test with")
    def test_is_elf(self):
        self.assertFalse(is_elf('/proc/meminfo'))
        self.assertFalse(is_elf('/'))
        self.assertTrue(is_elf(resolve('libm.so.6')))
