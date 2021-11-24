import e4s_cl
from e4s_cl import tests
from e4s_cl.cf.assets import add_builtin_profile, remove_builtin_profile
from e4s_cl.cli.commands.init import COMMAND as command

TEST_SYSTEM = '__test_system'

class InitTest(tests.TestCase):
    def setUp(self):
        add_builtin_profile(TEST_SYSTEM, {'name': TEST_SYSTEM})

    def tearDown(self):
        remove_builtin_profile(TEST_SYSTEM)

    def test_system(self):
        self.assertCommandReturnValue(0, command, f"--system {TEST_SYSTEM}")
