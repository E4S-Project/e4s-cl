import e4s_cl
from e4s_cl import tests
from e4s_cl.cli.commands.profile.create import COMMAND as command


class ProfileCreateTest(tests.TestCase):
    def test_create(self):
        stdout, stderr = self.assertCommandReturnValue(0, command, ['test01'])
        self.assertIn('Created a new profile named \'test01\'', stdout)
        self.assertFalse(stderr)
        stdout, stderr = self.assertCommandReturnValue(0, command, [
            'test02', '--files', '/tmp/e4s_cl/file', '--libraries',
            '/tmp/e4s_cl/library', '--image', '/tmp/e4s_cl/image', '--backend',
            'technology'
        ])
        self.assertIn('Created a new profile named \'test02\'', stdout)
        self.assertFalse(stderr)
        self.resetStorage()

    def test_unique(self):
        stdout, _ = self.assertCommandReturnValue(0, command, ['test01'])
        _, stderr = self.assertNotCommandReturnValue(0, command, ['test01'])
        self.assertIn('Created a new profile named \'test01\'', stdout)
        self.assertIn('profile create <profile_name>', stderr)
        self.assertIn('profile create: error: A profile named', stderr)
        self.assertIn('already exists', stderr)
        self.resetStorage()
