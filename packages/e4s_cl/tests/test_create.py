"""
Tests asserting the correct results of the profile create function
"""

from e4s_cl import tests
from e4s_cl.model.profile import Profile
from e4s_cl.cli.commands.profile.create import COMMAND as command


class ProfileCreateTest(tests.TestCase):
    """
    The actual tests. Profiles are deleted after every test.
    """
    def setUp(self):
        self.profile_name = 'test_profile'

    def tearDown(self):
        Profile.controller().unselect()
        self.resetStorage()

    def test_create(self):
        self.assertCommandReturnValue(0, command, [self.profile_name])
        self.assertTrue(Profile.controller().one({'name': self.profile_name}))

    def test_create_libraries(self):
        """
        Ensure libraries are added to the profile
        """
        libraries = [f'/tmp/e4s_cl/lib{no}.so' for no in range(5)]

        self.assertCommandReturnValue(
            0, command,
            [self.profile_name, '--libraries', ",".join(libraries)])

        profile = Profile.controller().one({'name': self.profile_name})
        self.assertTrue(profile)

        for libname in libraries:
            self.assertIn(libname, profile.get('libraries', []))

    def test_create_files(self):
        """
        Ensure files are added to the profile
        """
        files = [f'/tmp/e4s_cl/file{no}.txt' for no in range(5)]

        self.assertCommandReturnValue(
            0, command, [self.profile_name, '--files', ",".join(files)])

        profile = Profile.controller().one({'name': self.profile_name})
        self.assertTrue(profile)

        for filename in files:
            self.assertIn(filename, profile.get('files', []))

    def test_create_posix(self):
        """
        Ensure paths are formatted to be posix-compliant
        """
        posix = '/tmp/test.txt'
        non_posix = '/tmp/test.txt///////'

        self.assertCommandReturnValue(
            0, command, [self.profile_name, '--files', non_posix])

        profile = Profile.controller().one({'name': self.profile_name})
        self.assertTrue(profile)

        files = profile.get('files', [])
        self.assertNotIn(non_posix, files)
        self.assertIn(posix, files)

    def test_create_wrong_arguments(self):
        self.assertNotCommandReturnValue(0, command,
                                         [self.profile_name, '--when', 'now'])

        self.assertFalse(Profile.controller().one({'name': self.profile_name}))

    def test_unique(self):
        self.assertCommandReturnValue(0, command, [self.profile_name])
        _, stderr = self.assertNotCommandReturnValue(0, command,
                                                     [self.profile_name])
        self.assertIn('profile create <profile_name>', stderr)
        self.assertIn(
            f"profile create: error: A profile with name='{self.profile_name}' already exists",
            stderr)


fields = {
    ('--image', 'image', 'image:id', 'image_docker_style'),
    ('--image', 'image', '/path/to/image', 'image_singularity_style'),
    ('--backend', 'backend', 'singularity', 'backend'),
    ('--source', 'source', '/path/to/script.sh', 'source'),
    ('--wi4mpi', 'wi4mpi', '/usr/packages/wi4mpi', 'wi4mpi_location'),
    ('--wi4mpi_options', 'wi4mpi_options', '"-T mpich -F openmpi"', 'wi4mpi_options'),
}


def wrapper(option, field, argument, test_name):
    """
    Generate tests from a simple pattern to ensure all fields are correctly added
    """
    def generated_test(self):
        self.assertCommandReturnValue(0, command,
                                      [self.profile_name, option, argument])
        profile = Profile.controller().one({'name': self.profile_name})
        self.assertTrue(profile)
        self.assertEqual(argument, profile.get(field))

    generated_test.__name__ = f"test_{test_name}"

    return generated_test


for arguments in fields:
    test = wrapper(*arguments)
    setattr(ProfileCreateTest, test.__name__, test)
