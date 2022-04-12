import shlex
import tests
from e4s_cl.model.profile import Profile
from e4s_cl.cli.commands.profile.diff import COMMAND


class ProfileDiffTest(tests.TestCase):
    def tearDown(self):
        Profile.controller().unselect()
        self.resetStorage()

    def test_diff(self):
        Profile.controller().create({'name': 'lhs', 'files': ['/tmp/lhs_only', '/tmp/both']})
        Profile.controller().create({'name': 'rhs', 'files': ['/tmp/rhs_only', '/tmp/both']})

        stdout, _ = self.assertCommandReturnValue(0, COMMAND, shlex.split("lhs rhs"))
        self.assertNotIn('/tmp/both', stdout)
        self.assertIn('< /tmp/lhs_only', stdout)
        self.assertIn('> /tmp/rhs_only', stdout)

    def test_diff_missing_arg(self):
        Profile.controller().create({'name': 'lhs', 'files': ['/tmp/lhs_only', '/tmp/both']})

        self.assertNotCommandReturnValue(0, COMMAND, shlex.split("lhs"))
