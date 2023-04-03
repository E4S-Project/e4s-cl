"""
Tests ensuring the init command behaves as intented
"""

import os
from itertools import combinations
import tests
from tests import TEST_SYSTEM
from e4s_cl.util import which
from e4s_cl.model.profile import Profile
from e4s_cl.cf.libraries import resolve
from e4s_cl.cf.assets import add_builtin_profile, remove_builtin_profile
from e4s_cl.cli.commands.init import COMMAND


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

    def test_system_overwrite(self):
        self.assertCommandReturnValue(0, COMMAND, f"--system {TEST_SYSTEM}")
        self.assertEqual(Profile.controller().selected().get('name'),
                         TEST_SYSTEM)
        self.assertEqual(Profile.controller().count(), 1)
        self.assertCommandReturnValue(0, COMMAND, f"--system {TEST_SYSTEM}")
        self.assertEqual(Profile.controller().selected().get('name'),
                         TEST_SYSTEM)
        self.assertEqual(Profile.controller().count(), 1)

    def test_rename_system(self):
        self.assertCommandReturnValue(
            0, COMMAND, f"--profile init_test_profile --system {TEST_SYSTEM}")
        self.assertEqual(Profile.controller().selected().get('name'),
                         'init_test_profile')


groups = [
    [('--system', TEST_SYSTEM)],
    [
        ('--mpi', '/path/to/installation'),
        ('--launcher', '/path/to/binary'),
        ('--launcher_args', "'-np 8192'"),
    ],
]


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
