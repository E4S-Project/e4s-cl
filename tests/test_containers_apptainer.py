import tests
from e4s_cl import config
from tests.test_containers_sif_like import SifLikeContainerTestMixin

CONFIG_EXECUTABLE = tests.ASSETS / 'bin' / 'apptainer-conf'
DEFAULT_CONFIGURATION = config.CONFIGURATION
TEST_CONFIGURATION = config.Configuration.create_from_string(f"""
backends:
  apptainer:
    executable: '{CONFIG_EXECUTABLE}'
    options: ['--nocolor', '-s']
    exec_options: ['--hostname', 'XxmycoolcontainerxX']
""")


class ContainerTestApptainer(tests.TestCase, SifLikeContainerTestMixin):

    BACKEND_NAME = 'apptainer'
    ENV_PREFIX = 'APPTAINER'
    CONFIG_EXECUTABLE = tests.ASSETS / 'bin' / 'apptainer-conf'
    TEST_CONFIGURATION = TEST_CONFIGURATION
    DEFAULT_CONFIGURATION = DEFAULT_CONFIGURATION
