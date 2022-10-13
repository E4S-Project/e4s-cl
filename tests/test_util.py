import os
import tempfile
import tarfile
from pathlib import Path
import tests
from e4s_cl.util import which, path_accessible, safe_tar


class UtilTest(tests.TestCase):

    def test_which(self):
        executable = Path(which('ls'))
        self.assertTrue(executable.exists())
        self.assertTrue(executable.is_absolute())
        return executable.as_posix()

    @tests.skipIf("CICD" in os.environ, "gitlab testing environment")
    def test_access(self):
        self.assertTrue(path_accessible('/tmp', 'r'))
        self.assertTrue(path_accessible('/tmp', 'w'))
        self.assertTrue(path_accessible('/tmp', 'x'))
        self.assertTrue(path_accessible('/tmp', 'rwx'))
        self.assertFalse(path_accessible('/tmp/nonexistentfilehellothere',
                                         'w'))
        self.assertFalse(path_accessible('/root', 'w'))

    @tests.skipIf(True,
                  "Test hangs for no reason, disabling until fix is found")
    def test_safe_tar(self):
        with tempfile.NamedTemporaryFile(mode='w+b', suffix='.tgz') as archive:
            # Shape /home/foo/bar
            with tarfile.open(archive.name, 'w') as absolute:
                absolute_file = tarfile.TarInfo(str(Path.home() / '.bashrc'))
                absolute.addfile(absolute_file)
                self.assertFalse(safe_tar(absolute))

            # Shape ../foo/bar
            with tarfile.open(archive.name, 'w') as relative:
                relative_file = Path('..') / Path.cwd().name

                relative.add(relative_file, arcname=str(relative_file))
                self.assertFalse(safe_tar(relative))

            # Shape foo/../foo/bar
            with tarfile.open(archive.name, 'w') as safe_relative:
                current_path = Path.cwd()
                relative_file = Path(current_path.parts[0], '..', current_path)
                safe_relative.add(relative_file, arcname=str(relative_file))
                self.assertTrue(safe_tar(safe_relative))
