import re
from e4s_cl import tests
from e4s_cl.cli.commands.profile.create import COMMAND as create_command
from e4s_cl.cli.commands.profile.select import COMMAND as select_command
from e4s_cl.cli.commands.profile.list import COMMAND as list_command


class ProfileSelectTest(tests.TestCase):
    def setUp(self):
        self.profile_name = 'test_select_profile'

    def tearDown(self):
        self.resetStorage()

    def test_select(self):
        self.assertCommandReturnValue(0, create_command, [self.profile_name])
        self.assertCommandReturnValue(0, select_command, [self.profile_name])
        out, err = self.assertCommandReturnValue(0, list_command, [])
        self.assertTrue(re.search(f'\*.*{self.profile_name}', out))

    def test_select_nonexistent(self):
        out, err = self.assertCommandReturnValue(2, select_command,
                                                 ["Non-existent"])
