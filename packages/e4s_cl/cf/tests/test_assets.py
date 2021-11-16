import os
import pathlib
from e4s_cl import tests
from e4s_cl.cf.assets import binaries, profiles


class AssetsTest(tests.TestCase):
    def test_binaries(self):
        self.assertTrue(isinstance(binaries(), dict))

    def test_profiles(self):
        self.assertTrue(isinstance(profiles(), dict))
