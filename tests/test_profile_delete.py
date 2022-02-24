import tests
from e4s_cl.model.profile import Profile
from e4s_cl.cli.commands.profile.delete import COMMAND


class ProfileDeleteTest(tests.TestCase):
    def tearDown(self):
        Profile.controller().unselect()
        self.resetStorage()

    def test_delete(self):
        Profile.controller().create({'name': 'test01'})
        _, stderr = self.assertCommandReturnValue(0, COMMAND, ['test01'])
        self.assertIn('Deleted profile \'test01\'', stderr)

    def test_existence(self):
        _, stderr = self.assertNotCommandReturnValue(
            0, COMMAND, ['test01'])
        self.assertIn('profile delete <profile_name>', stderr)
        self.assertIn('profile delete: error: No', stderr)
