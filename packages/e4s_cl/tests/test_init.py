"""
Tests ensuring the init command behaves as intented
"""

from os import getenv
from itertools import combinations
from e4s_cl import tests
from e4s_cl.model.profile import Profile
from e4s_cl.cf.assets import add_builtin_profile, remove_builtin_profile
from e4s_cl.cli.commands.init import COMMAND

TEST_SYSTEM = '__test_system'


class InitTest(tests.TestCase):
    """
    Partial class definition: more tests are defined below
    """
    def setUp(self):
        add_builtin_profile(TEST_SYSTEM, {'name': TEST_SYSTEM})

    def tearDown(self):
        remove_builtin_profile(TEST_SYSTEM)
        Profile.controller().unselect()
        self.resetStorage()

    def test_system(self):
        self.assertCommandReturnValue(0, COMMAND, f"--system {TEST_SYSTEM}")
        self.assertEqual(Profile.controller().selected().get('name'),
                         TEST_SYSTEM)

    def test_wi4mpi(self):
        self.assertCommandReturnValue(
            0, COMMAND,
            "--wi4mpi /path/to/installation --wi4mpi_options '-T to -F from'")
        profile = Profile.controller().selected()

        self.assertTrue(profile)
        self.assertEqual(profile.get('wi4mpi'), '/path/to/installation')
        self.assertEqual(profile.get('wi4mpi_options'), '-T to -F from')

    def test_rename_system(self):
        self.assertCommandReturnValue(0, COMMAND, f"--profile init_test_profile --system {TEST_SYSTEM}")
        self.assertEqual(Profile.controller().selected().get('name'),
                         'init_test_profile')

    def test_rename_wi4mpi(self):
        self.assertCommandReturnValue(
            0, COMMAND,
            "--profile init_test_profile --wi4mpi /path/to/installation --wi4mpi_options '-T to -F from'")
        profile = Profile.controller().selected()

        self.assertTrue(profile)
        self.assertEqual(profile.get('name'), 'init_test_profile')
        self.assertEqual(profile.get('wi4mpi'), '/path/to/installation')
        self.assertEqual(profile.get('wi4mpi_options'), '-T to -F from')

    @tests.skipIf(not getenv('__E4S_CL_TEST_INIT'), "Init test from environment disabled")
    def test_init_environment(self):
        self.assertCommandReturnValue(0, COMMAND, [])

groups = [[('--system', TEST_SYSTEM)],
          [
              ('--wi4mpi', '/path/to/installation'),
              ('--wi4mpi_options', "'-T to -F from'"),
          ], [
              ('--mpi', '/path/to/installation'),
              ('--launcher', '/path/to/binary'),
              ('--launcher_args', "'-np 8192'"),
          ]]

def wrapper(option1, value1, option2, value2):
    """
    Generate tests from a simple pattern to ensure all fields are correctly added
    """
    def generated_test(self):
        self.assertNotCommandReturnValue(0, COMMAND,
                                      [option1, value1, option2, value2])

    generated_test.__name__ = f"test_{option1.strip('-')}_{option2.strip('-')}"

    return generated_test


for conflicting_left, conflicting_right in combinations(groups, 2):
    for argument1 in conflicting_left:
        for argument2 in conflicting_right:
            test = wrapper(*argument1, *argument2)
            setattr(InitTest, test.__name__, test)
