import tests
from e4s_cl.model.profile import Profile
from e4s_cl.cli.commands.profile.delete import COMMAND

PROFILE_NAMES = ['mpich', 'mvapich', 'openmpi']


class ProfileDeleteTest(tests.TestCase):

    def tearDown(self):
        Profile.controller().unselect()
        self.resetStorage()

    def test_delete(self):
        Profile.controller().create({'name': PROFILE_NAMES[0]})

        self.assertCommandReturnValue(0, COMMAND, [PROFILE_NAMES[0]])

        self.assertFalse(Profile.controller().one({'name': PROFILE_NAMES[0]}))

        Profile.controller().create({'name': PROFILE_NAMES[0]})
        Profile.controller().create({'name': PROFILE_NAMES[1]})
        Profile.controller().create({'name': PROFILE_NAMES[2]})

        self.assertCommandReturnValue(0, COMMAND, PROFILE_NAMES)

        self.assertFalse(Profile.controller().one({'name': PROFILE_NAMES[0]}))
        self.assertFalse(Profile.controller().one({'name': PROFILE_NAMES[1]}))
        self.assertFalse(Profile.controller().one({'name': PROFILE_NAMES[2]}))

    def test_existence(self):
        self.assertNotCommandReturnValue(0, COMMAND, ['test01'])

    def test_matching(self):
        Profile.controller().create({'name': PROFILE_NAMES[0]})
        Profile.controller().create({'name': PROFILE_NAMES[1]})
        Profile.controller().create({'name': PROFILE_NAMES[2]})

        # Fails due to 'm' matching two profiles
        self.assertNotCommandReturnValue(0, COMMAND, [PROFILE_NAMES[0][0]])

        # Succeeds due to 'o' matching only the last profile
        self.assertCommandReturnValue(0, COMMAND, [PROFILE_NAMES[2][0]])

        self.assertTrue(Profile.controller().one({'name': PROFILE_NAMES[0]}))
        self.assertTrue(Profile.controller().one({'name': PROFILE_NAMES[1]}))
        self.assertFalse(Profile.controller().one({'name': PROFILE_NAMES[2]}))
