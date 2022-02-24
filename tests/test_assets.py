import os
import pathlib
import tests
from e4s_cl.cf.assets import precompiled_binaries, builtin_profiles


class AssetsTest(tests.TestCase):
    def test_binaries(self):
        self.assertTrue(isinstance(precompiled_binaries(), dict))

    def test_profiles(self):
        self.assertTrue(isinstance(builtin_profiles(), dict))
