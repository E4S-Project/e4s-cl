"""
Ensure the profile list command functions as intended
"""

import tests
from e4s_cl import config
from e4s_cl.model.profile import Profile

tests.TestCase.setUpClass()
CONFIGURATION_FILE = tests.ASSETS / "e4s-cl.yaml"
TEST_CONFIGURATION = config.Configuration.create_from_file(CONFIGURATION_FILE)
config.update_configuration(TEST_CONFIGURATION)
from e4s_cl.cli.commands.profile.list import COMMAND


class ProfileListTest(tests.TestCase):
    """
    Partial class, as methods are added manually below
    """

    @classmethod
    def tearDownClass(cls):
        config.update_configuration(config.Configuration.default())

    def tearDown(self):
        self.resetStorage()

    def test_list(self):
        Profile.controller().create({"name": 'test01'})
        self.assertCommandReturnValue(0, COMMAND, "test01")

    def test_existence(self):
        _, stderr = self.assertNotCommandReturnValue(0, COMMAND, ['test01'])
        self.assertIn('profile list [profile_name] [profile_name]', stderr)
        self.assertIn('profile list: error:', stderr)

    def test_pattern(self):
        Profile.controller().create({"name": 'test01'})
        Profile.controller().create({"name": 'test02'})
        Profile.controller().create({"name": 'otherName01'})
        stdout, _ = self.assertCommandReturnValue(0, COMMAND, ['test0'])
        self.assertIn('test01', stdout)
        self.assertIn('test02', stdout)
        self.assertNotIn('otherName01', stdout)


def wrapper(key, value, test_name):
    """
    Generate tests from a simple pattern to ensure all fields are correctly shown
    """

    def generated_test(self):
        Profile.controller().create({'name': 'test01', key: value})
        stdout, _ = self.assertCommandReturnValue(0, COMMAND, '')
        if isinstance(value, list):
            self.assertIn(str(len(value)), stdout)
        else:
            self.assertIn(value, stdout)

    generated_test.__name__ = f"test_{test_name}"

    return generated_test


_fields = [('name', 'test_name', 'profile_list_name'),
           ('backend', 'test_back', 'profile_list_backend'),
           ('image', 'test_image', 'profile_list_image'),
           ('libraries', ['test_libraries01',
                          'test_libraries02'], 'profile_list_libraries_count'),
           ('files', ['test_files01', 'test_files02',
                      'test_files03'], 'profile_list_files_count')]

for arguments in _fields:
    test = wrapper(*arguments)
    setattr(ProfileListTest, test.__name__, test)
