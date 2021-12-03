"""
Setup a pipe for communication with child e4s-cl processes
"""

import os
from e4s_cl.error import InternalError

ENV_VAR = '__E4SCL_PIPE_FD'

OPEN_FD = int(os.environ.get(ENV_VAR, '-1'))


def attach():
    if OPEN_FD == -1:
        raise InternalError("No file descriptor set to send data !")

    return OPEN_FD


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
        self.opened_fds = os.pipe()
        os.set_inheritable(self.opened_fds[1], True)

        os.environ[ENV_VAR] = str(self.opened_fds[1])

    def __enter__(self):
        return self.opened_fds[0]

    def __exit__(self, type_, value, traceback):
        for fd in self.opened_fds:
            if fd:
                os.close(fd)

        del os.environ[ENV_VAR]
