"""
Ensure the profile show command functions as intended
"""

import tests
from e4s_cl.model.profile import Profile
from e4s_cl.cli.commands.profile.show import COMMAND as command


class ProfileShowTest(tests.TestCase):
    """
    Partial class, as methods are added manually below
    """

    def tearDown(self):
        self.resetStorage()

    def test_show(self):
        Profile.controller().create({"name": 'test01'})
        self.assertCommandReturnValue(0, command, ['test01'])

    def test_existence(self):
        _, stderr = self.assertNotCommandReturnValue(0, command, ['test01'])
        self.assertIn('profile show [arguments] <profile_name>', stderr)
        self.assertIn('profile show: error:', stderr)

    def test_pattern(self):
        Profile.controller().create({"name": 'test01'})
        Profile.controller().create({"name": 'test02'})
        Profile.controller().create({"name": 'test03'})
        Profile.controller().create({"name": 'otherName01'})
        self.assertNotCommandReturnValue(0, command, ['test'])
        self.assertCommandReturnValue(0, command, ['otherName'])


def wrapper(key, value, test_name):
    """
    Generate tests from a simple pattern to ensure all fields are correctly added
    """

    def generated_test(self):
        Profile.controller().create({'name': 'test01', key: value})
        stdout, _ = self.assertCommandReturnValue(0, command, 'test01')
        if isinstance(value, list):
            for element in value:
                self.assertIn(element, stdout)
        else:
            self.assertIn(value, stdout)

    generated_test.__name__ = f"test_{test_name}"

    return generated_test


_fields = [
    ('image', 'image:id', 'image_value'),
    ('backend', 'singularity', 'backend_value'),
    ('source', '/tmp/test.sh', 'source_value'),
    ('wi4mpi', '/usr/packages/wi4mpi', 'wi4mpi_value'),
    ('libraries', [f"lib{no}.so" for no in range(100)], 'libraries_values'),
    ('files', [f"file_{no}" for no in range(100)], 'files_values'),
]

for arguments in _fields:
    test = wrapper(*arguments)
    setattr(ProfileShowTest, test.__name__, test)
