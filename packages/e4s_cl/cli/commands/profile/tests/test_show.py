import e4s_cl
from e4s_cl import tests
from e4s_cl.cli.commands.profile.create import COMMAND as CreateCommand
from e4s_cl.cli.commands.profile.show import COMMAND as command


class ProfileShowTest(tests.TestCase):
    def test_show(self):
        stdout, stderr = self.assertCommandReturnValue(0, CreateCommand,
                                                       ['test01'])
        stdout, stderr = self.assertCommandReturnValue(0, command, ['test01'])
        fields = ["name"]
        for field in fields:
            self.assertIn(field + ":", stdout)
        stdout, stderr = self.assertCommandReturnValue(0, CreateCommand, [
            'test02', '--image', 'filepath', '--backend', 'container',
            '--files', '/path/to/file', '--libraries', '/lib64/libtest.so'
        ])
        stdout, stderr = self.assertCommandReturnValue(0, command, ['test02'])
        fields = ["name", "image", "backend", "files", "libraries"]
        for field in fields:
            self.assertIn(field + ":", stdout)
        self.resetStorage()

    def test_existence(self):
        stdout, stderr = self.assertNotCommandReturnValue(
            0, command, ['test01'])
        self.assertIn('profile show [arguments] <profile_name>', stderr)
        self.assertIn('profile show: error:', stderr)
        self.resetStorage()

    def test_pattern(self):
        _, _ = self.assertCommandReturnValue(0, CreateCommand, ['test01'])
        _, _ = self.assertCommandReturnValue(0, CreateCommand, ['test02'])
        _, _ = self.assertCommandReturnValue(0, CreateCommand, ['notATest03'])
        stdout, stderr = self.assertNotCommandReturnValue(0, command, ['test'])
        stdout, stderr = self.assertCommandReturnValue(0, command,
                                                       ['notATest'])
        self.resetStorage()
