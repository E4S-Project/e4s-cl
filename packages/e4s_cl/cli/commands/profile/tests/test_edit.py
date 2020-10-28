import e4s_cl
from e4s_cl import tests
from e4s_cl.cli.commands.profile.create import COMMAND as create_command
from e4s_cl.cli.commands.profile.edit import COMMAND as edit_command
from e4s_cl.cli.commands.profile.show import COMMAND as show_command


class ProfileEditTest(tests.TestCase):
    def setUp(self):
        self.files = ['/tmp/file1']
        self.libraries = ['/tmp/lib1.so']
        stdout, stderr = self.assertCommandReturnValue(0, create_command, [
            'test01', '--image', 'no image', '--backend', 'bash', '--files',
            *self.files, '--libraries', *self.libraries
        ])

    def tearDown(self):
        self.resetStorage()

    def test_edit(self):
        image = '/tmp/image.sif'
        backend = 'singularity'
        stdout, stderr = self.assertCommandReturnValue(
            0, edit_command,
            ['test01', '--image', image, '--backend', backend])
        stdout, stderr = self.assertCommandReturnValue(0, show_command,
                                                       ['test01'])
        self.assertIn(image, stdout)
        self.assertIn(backend, stdout)

    def test_add_file(self):
        filename = '/tmp/file2'
        stdout, stderr = self.assertCommandReturnValue(
            0, edit_command, ['test01', '--add-files', filename])
        stdout, stderr = self.assertCommandReturnValue(0, show_command,
                                                       ['test01'])
        self.assertIn(filename, stdout)

    def test_add_lib(self):
        filename = '/tmp/lib2.so'
        stdout, stderr = self.assertCommandReturnValue(
            0, edit_command, ['test01', '--add-libraries', filename])
        stdout, stderr = self.assertCommandReturnValue(0, show_command,
                                                       ['test01'])
        self.assertIn(filename, stdout)

    def test_remove_file(self):
        filename = self.files[0]
        stdout, stderr = self.assertCommandReturnValue(
            0, edit_command, ['test01', '--remove-files', filename])
        stdout, stderr = self.assertCommandReturnValue(0, show_command,
                                                       ['test01'])
        self.assertNotIn(filename, stdout)

    def test_remove_lib(self):
        filename = self.libraries[0]
        stdout, stderr = self.assertCommandReturnValue(
            0, edit_command, ['test01', '--remove-libraries', filename])
        stdout, stderr = self.assertCommandReturnValue(0, show_command,
                                                       ['test01'])
        self.assertNotIn(filename, stdout)

    def test_add_twice_file(self):
        filename = self.files[0]
        stdout, stderr = self.assertCommandReturnValue(
            0, edit_command, ['test01', '--add-files', filename])
        self.assertIn("File %s already in profile's files" % filename, stderr)
        filename = "%s/" % self.files[0]
        stdout, stderr = self.assertCommandReturnValue(
            0, edit_command, ['test01', '--add-files', filename])
        self.assertIn("File %s already in profile's files" % self.files[0],
                      stderr)

    def test_add_twice_lib(self):
        filename = self.libraries[0]
        stdout, stderr = self.assertCommandReturnValue(
            0, edit_command, ['test01', '--add-libraries', filename])
        self.assertIn("File %s already in profile's libraries" % filename,
                      stderr)
        filename = "%s/" % self.libraries[0]
        stdout, stderr = self.assertCommandReturnValue(
            0, edit_command, ['test01', '--add-libraries', filename])
        self.assertIn(
            "File %s already in profile's libraries" % self.libraries[0],
            stderr)

    def test_remove_nonexistent_file(self):
        filename = "nonexistent"
        stdout, stderr = self.assertCommandReturnValue(
            0, edit_command, ['test01', '--remove-files', filename])
        self.assertIn("File %s not in profile's files" % filename, stderr)

    def test_remove_nonexistent_lib(self):
        filename = "nonexistent"
        stdout, stderr = self.assertCommandReturnValue(
            0, edit_command, ['test01', '--remove-libraries', filename])
        self.assertIn("File %s not in profile's libraries" % filename, stderr)
