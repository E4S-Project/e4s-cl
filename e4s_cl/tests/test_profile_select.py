"""
Ensure the profile select command behaves properly
"""
from e4s_cl import tests
from e4s_cl.model.profile import Profile
from e4s_cl.cli.commands.profile.select import COMMAND


class ProfileSelectTest(tests.TestCase):
    """
    Profiles are erased after each tests
    """
    def setUp(self):
        self.profile_name = 'test_select_profile'

    def tearDown(self):
        Profile.controller().unselect()
        self.resetStorage()

    def test_select(self):
        Profile.controller().create({'name': self.profile_name})
        self.assertCommandReturnValue(0, COMMAND, [self.profile_name])
        self.assertEqual(Profile.controller().selected().get('name'),
                         self.profile_name)

    def test_select_nonexistent(self):
        self.assertCommandReturnValue(2, COMMAND, ["non-existent"])
