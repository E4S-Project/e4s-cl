"""
Setup a pipe for communication with child e4s-cl processes
"""

import os
import errno
from pathlib import Path
from e4s_cl.logger import get_logger
from e4s_cl.error import InternalError
from e4s_cl.util import hash256

ENV_VAR = '__E4SCL_PIPE_FD'
ENV_VAR_NAMED = '__E4SCL_PIPE_NAME'

OPEN_FD = int(os.environ.get(ENV_VAR, '-1'))
NAMED_PIPE = str(os.environ.get(ENV_VAR_NAMED, ''))

NAMED_PIPE_DIR = Path('/var/tmp/e4s-cl')

DATA_SIZE = 1024**3

LOGGER = get_logger(__name__)


def attach():
    if OPEN_FD == -1 and not NAMED_PIPE:
        raise InternalError("No available pipe set to send data !")

    if OPEN_FD > -1:
        return OPEN_FD
    return os.open(NAMED_PIPE, os.O_WRONLY)


class Pipe():
    """
    Context manager to open a pipe. Child processes will be able to access the
    writing end by using pipe.attach()
    """

    def __init__(self):
        """
        -> int
        returns a fd, the reading end of a pipe
        """
        self.fd_read, self.fd_write = os.pipe()
        os.set_inheritable(self.fd_write, True)

        os.environ[ENV_VAR] = str(self.fd_write)

        LOGGER.debug("Creating pipe with fds %d/%d", self.fd_read,
                     self.fd_write)

    def __enter__(self):

        def pipe_read():
            data = os.read(self.fd_read, DATA_SIZE).decode()

            for fd in (self.fd_read, self.fd_write):
                if fd:
                    os.close(fd)

            return data

        return pipe_read

    def __exit__(self, type_, value, traceback):
        del os.environ[ENV_VAR]


class NamedPipe():
    """
    Context manager to open a named pipe. Child processes will be able to
    access the writing end by using pipe.attach()
    """

    def __init__(self) -> None:
        Path.mkdir(NAMED_PIPE_DIR, parents=True, exist_ok=True)
        self.pipe = Path(NAMED_PIPE_DIR, hash256(str(os.getpid())))

        try:
            os.mkfifo(self.pipe.as_posix())
        except OSError as err:
            if err.errno != errno.EEXIST:
                raise err

        self.fd_read = os.open(self.pipe.as_posix(),
                               os.O_RDONLY | os.O_NONBLOCK)

        LOGGER.debug("Creating named pipe in %s", self.pipe.as_posix())

        os.environ[ENV_VAR_NAMED] = self.pipe.as_posix()

    def __enter__(self) -> Path:

        def pipe_read():
            data = os.read(self.fd_read, DATA_SIZE).decode()

            self.pipe.unlink(missing_ok=True)

            return data

        return pipe_read

    def __exit__(self, type_, value, traceback):
        del os.environ[ENV_VAR_NAMED]
