import os
import shlex
import json
import tests
from io import StringIO
from pathlib import Path
from unittest.mock import patch
from e4s_cl import config
from e4s_cl.variables import set_dry_run
from e4s_cl.cf.launchers import LAUNCHERS
from e4s_cl.cli.commands.launch import COMMAND, Parameters, _format_execute
from e4s_cl.cli.cli_view import CreateCommand
from e4s_cl.model.profile import Profile


class LaunchTest(tests.TestCase):

    @classmethod
    def setUpClass(cls):
        tests.TestCase.setUpClass()
        CONFIGURATION_FILE = tests.ASSETS / "e4s-cl.yaml"
        TEST_CONFIGURATION = config.Configuration.create_from_file(
            CONFIGURATION_FILE)
        config.update_configuration(TEST_CONFIGURATION)

    @classmethod
    def tearDownClass(cls):
        config.update_configuration(config.Configuration.default())

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

    def test_backend_args_forwarded_to_execute(self):
        params = Parameters(
            backend='containerless',
            image='None',
            backend_args='--fakeroot --cleanenv',
        )

        command = _format_execute(params)
        self.assertContainsInOrder([
            '--backend-args',
            '--fakeroot --cleanenv',
        ], command)


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
