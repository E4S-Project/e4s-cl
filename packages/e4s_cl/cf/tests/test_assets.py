import os
import pathlib
from e4s_cl import tests
from e4s_cl.cf.assets import binaries


class AssetsTest(tests.TestCase):
    def test_binaries(self):
        self.assertTrue(isinstance(binaries(), dict))
