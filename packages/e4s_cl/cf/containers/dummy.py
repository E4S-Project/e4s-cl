from e4s_cl import logger
from e4s_cl.util import create_subprocess_exp
from e4s_cl.cf.libraries import host_libraries
from e4s_cl.cf.containers import Container, FileOptions

LOGGER = logger.get_logger(__name__)

DEBUG_BACKEND = True
NAME = 'dummy'
EXECUTABLES = ['bash']
MIMES = []


class DummyContainer(Container):
    def run(self, command, redirect_stdout=False):
        pass


CLASS = DummyContainer
