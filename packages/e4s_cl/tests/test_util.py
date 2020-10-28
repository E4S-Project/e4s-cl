import pathlib
from e4s_cl import tests
from e4s_cl.util import opened_files, which


class UtilTest(tests.TestCase):
    def test_opened_files(self):
        returncode, files = opened_files(['cat', '/dev/null'])
        self.assertEqual(returncode, 0)
        self.assertIn('/dev/null', [path.as_posix() for path in files])

    def test_which(self):
        path = which('ls')
        executable = pathlib.Path(path)
        self.assertTrue(executable.exists())
        self.assertTrue(executable.is_absolute())
        return executable.as_posix()
