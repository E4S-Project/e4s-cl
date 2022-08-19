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
from e4s_cl.cli.commands.launch import COMMAND
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

    @patch('sys.stdout', new_callable=StringIO)
    def test_configured_launch(self, stdout):
        set_dry_run(True)
        COMMAND.main(
            shlex.split(
                f"--backend containerless --image None mpirun hostname"))
        self.assertIn('-n 8', stdout.getvalue())


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
