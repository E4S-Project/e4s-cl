from e4s_cl import tests
from e4s_cl.model.profile import Profile
from e4s_cl.cli.commands.profile.copy import COMMAND


class ProfileCopyTest(tests.TestCase):
    def tearDown(self):
        Profile.controller().unselect()
        self.resetStorage()

    def test_copy(self):
        Profile.controller().create({'name': 'test01'})
        self.assertCommandReturnValue(0, COMMAND, ['test01', 'test02'])

        copy = Profile.controller().one({'name': 'test02'})
        self.assertTrue(copy)
        self.assertEqual(copy.get('name'), 'test02')

    def test_existence(self):
        self.assertNotCommandReturnValue(0, COMMAND, ['test01', 'test02'])
