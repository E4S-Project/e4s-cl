"""
Ensure the profile list command functions as intended
"""

from e4s_cl import tests
from e4s_cl.model.profile import Profile
from e4s_cl.cli.commands.profile.list import COMMAND as command


class ProfileListTest(tests.TestCase):
    """
    Partial class, as methods are added manually below
    """
    def tearDown(self):
        self.resetStorage()

    def test_list(self):
        Profile.controller().create({"name": 'test01'})
        self.assertCommandReturnValue(0, command, "test01")
    
    def test_existence(self):
        _, stderr = self.assertNotCommandReturnValue(
            0, command, ['test01'])
        self.assertIn('profile list [profile_name] [profile_name]', stderr)
        self.assertIn('profile list: error:', stderr)

    def test_pattern(self):
        Profile.controller().create({"name": 'test01'})
        Profile.controller().create({"name": 'test02'})
        Profile.controller().create({"name": 'otherName01'})
        stdout, _ = self.assertCommandReturnValue(0, command, ['test0'])
        self.assertIn('test01', stdout)
        self.assertIn('test02', stdout)
        self.assertNotIn('otherName01', stdout)


