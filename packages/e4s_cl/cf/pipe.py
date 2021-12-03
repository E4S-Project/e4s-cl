"""
Setup a pipe for communication with child e4s-cl processes
"""

import os
from e4s_cl.error import InternalError

ENV_VAR = '__E4SCL_PIPE_FD'

OPEN_FD = int(os.environ.get(ENV_VAR, '-1'))

OPENED_PIPE = (None, None)


def attach():
    if OPEN_FD == -1:
        raise InternalError("No file descriptor set to send data !")

    return OPEN_FD


def create():
    """
    -> int
    returns a fd, the reading end of a pipe
    """
    OPENED_PIPE = os.pipe()
    os.set_inheritable(OPENED_PIPE[1], True)

    os.environ[ENV_VAR] = str(OPENED_PIPE[1])

    return OPENED_PIPE[0]

def close():
    for fd in OPENED_PIPE:
        if fd:
            os.close(fd)

    os.unsetenv(ENV_VAR)
