import pathlib
import tests
from e4s_cl.util import which, path_accessible


class UtilTest(tests.TestCase):
    def test_which(self):
        path = which('ls')
        executable = pathlib.Path(path)
        self.assertTrue(executable.exists())
        self.assertTrue(executable.is_absolute())
        return executable.as_posix()

    def test_access(self):
        self.assertTrue(path_accessible('/tmp', 'r'))
        self.assertTrue(path_accessible('/tmp', 'w'))
        self.assertTrue(path_accessible('/tmp', 'x'))
        self.assertTrue(path_accessible('/tmp', 'rwx'))
        self.assertFalse(path_accessible('/tmp/nonexistentfilehellothere', 'w'))
        self.assertFalse(path_accessible('/root', 'w'))
