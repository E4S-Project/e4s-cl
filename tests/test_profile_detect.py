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

__TEST_LIBRARY_SONAME__ = "libz.so"
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
    def test_filter_files(self):
        with NamedTemporaryFile() as datafile:
            library = resolve(__TEST_LIBRARY_SONAME__)

            libraries, files = filter_files(
                map(
                    Path, {
                        *__BLACKLISTED_FILES__, __TEST_LIBRARY_NON_STANDARD__,
                        library, datafile.name
                    }))

            self.assertIn(library, libraries)
            self.assertIn(datafile.name, files)
            for filename in __BLACKLISTED_FILES__:
                self.assertNotIn(filename, files)
                self.assertNotIn(filename, libraries)

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
