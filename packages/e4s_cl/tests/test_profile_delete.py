import e4s_cl
from e4s_cl import tests
from e4s_cl.cli.commands.profile.create import COMMAND as CreateCommand
from e4s_cl.cli.commands.profile.delete import COMMAND as command


class ProfileDeleteTest(tests.TestCase):
    def test_delete(self):
        stdout, stderr = self.assertCommandReturnValue(0, CreateCommand,
                                                       ['test01'])
        stdout, stderr = self.assertCommandReturnValue(0, command, ['test01'])
        self.assertIn('Deleted profile \'test01\'', stderr)
        self.resetStorage()

    def test_existence(self):
        stdout, stderr = self.assertNotCommandReturnValue(
            0, command, ['test01'])
        self.assertIn('profile delete <profile_name>', stderr)
        self.assertIn('profile delete: error: No', stderr)
        self.resetStorage()
