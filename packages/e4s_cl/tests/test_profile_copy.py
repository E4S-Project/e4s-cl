import e4s_cl
from e4s_cl import tests
from e4s_cl.cli.commands.profile.create import COMMAND as CreateCommand
from e4s_cl.cli.commands.profile.copy import COMMAND as command


class ProfileCopyTest(tests.TestCase):
    def test_copy(self):
        stdout, stderr = self.assertCommandReturnValue(0, CreateCommand,
                                                       ['test01'])
        stdout, stderr = self.assertCommandReturnValue(0, command,
                                                       ['test01', 'test02'])
        self.resetStorage()

    def test_existence(self):
        stdout, stderr = self.assertNotCommandReturnValue(
            0, command, ['test01', 'test02'])
        self.resetStorage()
