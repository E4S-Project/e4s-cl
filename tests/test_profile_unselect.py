"""
Ensure the profile unselect command behaves properly
"""
import tests
from e4s_cl.model.profile import Profile
from e4s_cl.error import ProfileSelectionError
from e4s_cl.cli.commands.profile.unselect import COMMAND


class ProfileUnselectTest(tests.TestCase):
    """
    Profiles are erased after each tests
    """
    def setUp(self):
        self.profile_name = 'test_unselect_profile'
        profile = Profile.controller().create({'name': self.profile_name})
        Profile.controller().select(profile)

    def tearDown(self):
        Profile.controller().unselect()
        self.resetStorage()

    def test_unselect(self):
        self.assertCommandReturnValue(0, COMMAND, [self.profile_name])
        self.assertRaises(ProfileSelectionError, Profile.controller().selected)

    def test_unselect_nonexistent(self):
        self.assertCommandReturnValue(2, COMMAND, ["non-existent"])
