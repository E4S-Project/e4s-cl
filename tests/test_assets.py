import os
import pathlib
import tests
from e4s_cl.cf.assets import (precompiled_binaries, builtin_profiles,
                              add_precompiled_binary, add_builtin_profile,
                              _import_asset, SAMPLE_BINARY_TABLE)


class AssetsTest(tests.TestCase):
    def setUp(self):
        self.resetStorage()

    def tearDown(self):
        self.resetStorage()

    def test_binaries(self):
        self.assertTrue(isinstance(precompiled_binaries(), dict))

    def test_profiles(self):
        self.assertTrue(isinstance(builtin_profiles(), dict))

    def test_import_precompiled_binary(self):
        add_precompiled_binary('libffi.so.7', '/tmp/doesnotexist')

        self.assertIn('libffi.so.7', precompiled_binaries())

    def test_import_builtin_profile(self):
        add_builtin_profile('spoutnik', {'files': ['/tmp']})

        self.assertIn('spoutnik', builtin_profiles())
    
    def test_import_builtin_faulty_profile_type(self):
        with self.assertRaises(ValueError):
            add_builtin_profile('spoutnik', {'files': '/tmp'})
        self.assertNotIn('spoutnik', builtin_profiles())

    def test_import_builtin_faulty_profile_key(self):
        with self.assertRaises(ValueError):
            add_builtin_profile('spoutnik', {'file': ['/tmp']})
        self.assertNotIn('spoutnik', builtin_profiles())
    
    def test_import_bad_asset(self):
        _import_asset('notakey', {'name': 'profile'}, SAMPLE_BINARY_TABLE)
        self.assertNotIn('notakey', builtin_profiles())

    def test_import_existing_asset(self):
        _import_asset('soname', {
            'soname': 'libffi.so.7',
            'path': '/tmp/doesnotexist'
        }, SAMPLE_BINARY_TABLE)
        _import_asset('soname', {
            'soname': 'libffi.so.7',
            'path': '/tmp/overwrite'
        }, SAMPLE_BINARY_TABLE)

        self.assertEqual(precompiled_binaries().get('libffi.so.7'),
                         '/tmp/overwrite')
