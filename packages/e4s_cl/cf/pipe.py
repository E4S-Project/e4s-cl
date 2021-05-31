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


def create():
    """
    -> int
    returns a fd, the reading end of a pipe
    """
    fdr, fdw = os.pipe()
    os.set_inheritable(fdw, True)

    os.environ[ENV_VAR] = str(fdw)

    return fdr
