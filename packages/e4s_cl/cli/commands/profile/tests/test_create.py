import e4s_cl
from e4s_cl import tests
from e4s_cl.cli.commands.profile.create import COMMAND as create_command
from e4s_cl.cli.commands.profile.list import COMMAND as list_command
from e4s_cl.cli.commands.profile.show import COMMAND as show_command


class ProfileCreateTest(tests.TestCase):
    def setUp(self):
        self.profile_name = 'test_profile'

    def tearDown(self):
        self.resetStorage()

    def test_create(self):
        stdout, stderr = self.assertCommandReturnValue(0, create_command,
                                                       [self.profile_name])
        stdout, stderr = self.assertCommandReturnValue(0, list_command, [])
        self.assertIn(self.profile_name, stdout)

    def test_create_image(self):
        stdout, stderr = self.assertCommandReturnValue(0, create_command, [
            self.profile_name, '--image', '/tmp/e4s_cl/image', '--backend',
            'technology'
        ])
        stdout, stderr = self.assertCommandReturnValue(0, list_command, [])
        self.assertIn(self.profile_name, stdout)

    def test_create_libraries(self):
        libraries = ['/tmp/e4s_cl/lib%d.so' % k for k in range(5)]

        stdout, stderr = self.assertCommandReturnValue(
            0, create_command, [self.profile_name, '--libraries', ",".join(libraries)])

        stdout, stderr = self.assertCommandReturnValue(0, list_command, [])
        self.assertIn(self.profile_name, stdout)

        stdout, stderr = self.assertCommandReturnValue(0, show_command,
                                                       [self.profile_name])
        for libname in libraries:
            self.assertIn(libname, stdout)

    def test_create_files(self):
        files = ['/tmp/e4s_cl/file%d.txt' % k for k in range(5)]

        stdout, stderr = self.assertCommandReturnValue(
            0, create_command, [self.profile_name, '--files', ",".join(files)])

        stdout, stderr = self.assertCommandReturnValue(0, list_command, [])
        self.assertIn(self.profile_name, stdout)

        stdout, stderr = self.assertCommandReturnValue(0, show_command,
                                                       [self.profile_name])
        for filename in files:
            self.assertIn(filename, stdout)

    def test_create_posix(self):
        posix = '/tmp/test.txt'
        non_posix = '/tmp/test.txt///////'

        stdout, stderr = self.assertCommandReturnValue(
            0, create_command, [self.profile_name, '--files', non_posix])

        stdout, stderr = self.assertCommandReturnValue(0, list_command, [])
        self.assertIn(self.profile_name, stdout)

        stdout, stderr = self.assertCommandReturnValue(0, show_command,
                                                       [self.profile_name])
        self.assertNotIn(non_posix, stdout)
        self.assertIn(posix, stdout)

    def test_create_wrong_arguments(self):
        stdout, stderr = self.assertNotCommandReturnValue(
            0, create_command, [self.profile_name, '--when', 'now'])

        stdout, stderr = self.assertCommandReturnValue(0, list_command, [])
        self.assertNotIn(self.profile_name, stdout)

    def test_unique(self):
        stdout, stderr = self.assertCommandReturnValue(0, create_command,
                                                       [self.profile_name])
        stdout, stderr = self.assertNotCommandReturnValue(
            0, create_command, [self.profile_name])
        self.assertIn('profile create <profile_name>', stderr)
        self.assertIn(
            "profile create: error: A profile with name='%s' already exists" %
            self.profile_name, stderr)
