import os
from tempfile import NamedTemporaryFile
from shlex import split
from sotools.linker import resolve
from pathlib import Path
import tests
from e4s_cl.util import which
from e4s_cl.variables import ParentStatus
from e4s_cl.model.profile import Profile
from e4s_cl.cli.commands.profile.detect import (filter_files, COMMAND)
from e4s_cl.model.profile import Profile

__TEST_LIBRARY_SONAME__ = "libmpi.so"
__TEST_LIBRARY_NON_STANDARD__ = Path(
    Path(__file__).parent, "assets", "libgver.so.0").as_posix()
__BLACKLISTED_FILES__ = {
    "/dev/null", "/proc/self/fd/0", "/root", "/root/file", "/etc/ld.so.cache"
}
__TEST_BINARY__ = f"file"
__TEST_ARGS__ = f"{resolve(__TEST_LIBRARY_SONAME__)}"


class ProfileDetectTest(tests.TestCase):

    def tearDown(self):
        Profile.controller().unselect()
        self.resetStorage()

    @tests.skipIf(not resolve(__TEST_LIBRARY_SONAME__),
                  f"{__TEST_LIBRARY_SONAME__} not found on this system")
    def test_filter_files_lib(self):
        library = resolve(__TEST_LIBRARY_SONAME__)

        libraries, files = filter_files([Path(library)])

        self.assertIn(library, libraries)
        self.assertFalse(files)

    def test_filter_files_non_std_lib(self):
        libraries, files = filter_files([Path(__TEST_LIBRARY_NON_STANDARD__)])

        self.assertFalse(libraries)
        self.assertIn(__TEST_LIBRARY_NON_STANDARD__, files)

    def test_filter_files_existing_file(self):
        with NamedTemporaryFile(dir=os.getcwd()) as datafile:
            libraries, files = filter_files([Path(datafile.name)])

            self.assertFalse(libraries)
            self.assertIn(datafile.name, files)

    def test_filter_files_blacklisted(self):
        libraries, files = filter_files(map(Path, *__BLACKLISTED_FILES__))

        self.assertFalse(libraries)
        self.assertFalse(files)

    @tests.skipIf(not which(__TEST_BINARY__),
                  f"{__TEST_BINARY__} not found on this system")
    def test_profile_detect_new_profile(self):
        self.assertCommandReturnValue(
            0, COMMAND,
            split(
                f"-p __test_profile_detect {__TEST_BINARY__} {__TEST_ARGS__}"))

    @tests.skipIf(not which(__TEST_BINARY__),
                  f"{__TEST_BINARY__} not found on this system")
    def test_profile_detect_existing_profile(self):
        profile = Profile.controller().create(
            {'name': '__test_profile_detect'})

        self.assertCommandReturnValue(
            0, COMMAND,
            split(
                f"-p __test_profile_detect {__TEST_BINARY__} {__TEST_ARGS__}"))

    @tests.skipIf(not which(__TEST_BINARY__),
                  f"{__TEST_BINARY__} not found on this system")
    def test_profile_detect_selected_profile(self):
        profile = Profile.controller().create(
            {'name': '__test_profile_detect'})
        Profile.controller().select(profile)

        self.assertCommandReturnValue(
            0, COMMAND, split(f"{__TEST_BINARY__} {__TEST_ARGS__}"))

    @tests.skipIf(not which(__TEST_BINARY__),
                  f"{__TEST_BINARY__} not found on this system")
    def test_profile_detect_no_profile(self):
        self.assertNotCommandReturnValue(
            0, COMMAND, split(f"{__TEST_BINARY__} {__TEST_ARGS__}"))

    @tests.skipIf(not which(__TEST_BINARY__),
                  f"{__TEST_BINARY__} not found on this system")
    def test_profile_detect_child(self):
        with ParentStatus():
            self.assertCommandReturnValue(
                0, COMMAND, split(f"{__TEST_BINARY__} {__TEST_ARGS__}"))

    def test_profile_detect_error(self):
        self.assertNotCommandReturnValue(0, COMMAND,
                                         split("bash -c \"exit 1\""))

    def test_profile_detect_no_command(self):
        self.assertNotCommandReturnValue(0, COMMAND, [])
