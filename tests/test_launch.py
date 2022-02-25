import os
import shlex
import json
import tests
from e4s_cl.variables import set_dry_run
from e4s_cl.cf.launchers import LAUNCHERS
from e4s_cl.cli.commands.launch import COMMAND
from e4s_cl.cli.cli_view import CreateCommand
from e4s_cl.model.profile import Profile


class LaunchTest(tests.TestCase):

    def setUp(self):
        self.resetStorage()

        data = os.getenv('__E4S_CL_TEST_PROFILE', {})
        if not data:
            return

        controller = Profile.controller()
        profile = controller.create(json.loads(data))
        controller.select(profile)

    def tearDown(self):
        self.resetStorage()


def wrapper(launcher):

    def generated(self):
        set_dry_run(True)
        self.assertCommandReturnValue(
            0, COMMAND,
            shlex.split(
                f"--backend containerless --image None {launcher} hostname"))

    generated.__name__ = f"test_launch_{launcher}"

    return generated


for launcher in LAUNCHERS:
    test = wrapper(launcher)
    setattr(LaunchTest, test.__name__, test)
