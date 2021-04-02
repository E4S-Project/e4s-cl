"""
Dummy backend used to run false containers using bash
"""

import shlex
from e4s_cl.util import create_subprocess_exp
from e4s_cl.cf.containers import Container

NAME = 'dummy'
EXECUTABLES = ['bash']
MIMES = ['e4s_cl_test']
DEBUG_BACKEND = True


class DummyContainer(Container):
    """
    Run a command using bash
    """
    def run(self, command, redirect_stdout=False):
        container_cmd = "%(executable)s -c \"%(command)s\"" % {
            'executable': '/bin/bash',
            'command': ' '.join(command)
        }

        _, output = create_subprocess_exp(shlex.split(container_cmd),
                                          env=self.env,
                                          redirect_stdout=redirect_stdout)
        return output


CLASS = DummyContainer
