import pathlib
from e4s_cl import tests
from e4s_cl.util import which


class UtilTest(tests.TestCase):
    def test_which(self):
        path = which('ls')
        executable = pathlib.Path(path)
        self.assertTrue(executable.exists())
        self.assertTrue(executable.is_absolute())
        return executable.as_posix()
