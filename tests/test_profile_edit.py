"""
Tests asserting the correct behaviour of the profile edit command
"""

import tests
from e4s_cl.model.profile import Profile
from e4s_cl.cli.commands.profile.edit import COMMAND


class ProfileEditTest(tests.TestCase):
    """
    The actual tests. Profiles are deleted after every test. More tests are
    added by the code snippet after the class definition.
    """
    def setUp(self):
        self.profile_name = 'test01'
        self.files = ['/tmp/file1']
        self.libraries = ['/tmp/lib1.so']

        Profile.controller().create({
            "name": self.profile_name,
            "image": 'no image',
            "backend": 'bash',
            "source": None,
            "wi4mpi": None,
            "wi4mpi_options": None,
            "files": self.files,
            "libraries": self.libraries,
        })

    def tearDown(self):
        Profile.controller().unselect()
        self.resetStorage()

    def test_add_file(self):
        filename = '/tmp/file2'
        self.assertCommandReturnValue(
            0, COMMAND, [self.profile_name, '--add-files', filename])

        profile = Profile.controller().one({'name': self.profile_name})
        self.assertTrue(profile)
        self.assertIn(filename, profile.get('files', []))

    def test_add_lib(self):
        filename = '/tmp/lib2.so'
        self.assertCommandReturnValue(
            0, COMMAND, [self.profile_name, '--add-libraries', filename])

        profile = Profile.controller().one({'name': self.profile_name})
        self.assertTrue(profile)
        self.assertIn(filename, profile.get('libraries', []))

    def test_remove_file(self):
        filename = self.files[0]
        self.assertCommandReturnValue(
            0, COMMAND, [self.profile_name, '--remove-files', filename])

        profile = Profile.controller().one({'name': self.profile_name})
        self.assertTrue(profile)
        self.assertNotIn(filename, profile.get('files', []))

    def test_remove_lib(self):
        filename = self.libraries[0]
        self.assertCommandReturnValue(
            0, COMMAND, [self.profile_name, '--remove-libraries', filename])
        profile = Profile.controller().one({'name': self.profile_name})
        self.assertTrue(profile)
        self.assertNotIn(filename, profile.get('libraries', []))

    def test_add_twice_file(self):
        filename = self.files[0]
        _, stderr = self.assertCommandReturnValue(
            0, COMMAND, [self.profile_name, '--add-files', filename])
        self.assertIn(f"File {filename} already in profile's files", stderr)
        filename = f"{self.files[0]}/"
        _, stderr = self.assertCommandReturnValue(
            0, COMMAND, [self.profile_name, '--add-files', filename])
        self.assertIn(f"File {self.files[0]} already in profile's files",
                      stderr)

    def test_add_twice_lib(self):
        filename = self.libraries[0]
        _, stderr = self.assertCommandReturnValue(
            0, COMMAND, [self.profile_name, '--add-libraries', filename])
        self.assertIn(f"File {filename} already in profile's libraries",
                      stderr)
        filename = f"{self.libraries[0]}/"
        _, stderr = self.assertCommandReturnValue(
            0, COMMAND, [self.profile_name, '--add-libraries', filename])
        self.assertIn(
            f"File {self.libraries[0]} already in profile's libraries", stderr)

    def test_remove_nonexistent_file(self):
        filename = "nonexistent"
        _, stderr = self.assertCommandReturnValue(
            0, COMMAND, [self.profile_name, '--remove-files', filename])
        self.assertIn(f"File {filename} not in profile's files", stderr)

    def test_remove_nonexistent_lib(self):
        filename = "nonexistent"
        _, stderr = self.assertCommandReturnValue(
            0, COMMAND, [self.profile_name, '--remove-libraries', filename])
        self.assertIn(f"File {filename} not in profile's libraries", stderr)


fields = {
    ('--image', 'image:id', 'image', 'edit_image'),
    ('--backend', 'singularity', 'backend', 'edit_backend'),
    ('--source', '/tmp/test.sh', 'source', 'edit_source'),
    ('--wi4mpi', '/usr/packages/installation', 'wi4mpi', 'edit_wi4mpi'),
    ('--wi4mpi_options', "'-T to -F from'", 'wi4mpi_options', 'edit_wi4mpi_options'),
}


def wrapper(option, value, field, test_name):
    """
    Generate tests from a template and a list of options
    """
    def generated_test(self):
        self.assertCommandReturnValue(0, COMMAND,
                                      [self.profile_name, option, value])

        profile = Profile.controller().one({'name': self.profile_name})
        self.assertTrue(profile)
        self.assertEqual(value, profile.get(field))

    generated_test.__name__ = f"test_{test_name}"

    return generated_test


for arguments in fields:
    test = wrapper(*arguments)
    setattr(ProfileEditTest, test.__name__, test)
