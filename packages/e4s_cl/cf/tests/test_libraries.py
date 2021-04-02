import os
import pathlib
from unittest import skipIf
from e4s_cl import tests
from e4s_cl.util import which
from e4s_cl.cf.libraries import host_libraries, ldd, resolve


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
