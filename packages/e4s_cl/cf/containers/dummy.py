"""
Dummy backend used to run false containers using bash
"""

from e4s_cl.util import create_subprocess_exp
from e4s_cl.cf.containers import Container

EXECUTABLES = ['bash']
MIMES = ['e4s_cl_test']


class DummyContainer(Container):
    """
    Run a command using bash
    """
    def run(self, command, redirect_stdout=False):
        container_cmd = "%(executable)s -c %(command)s" % {
            'executable': '/bin/bash',
            'command': ' '.join(command)
        }

        _, output = create_subprocess_exp(container_cmd.split(),
                                          env=self.env,
                                          redirect_stdout=redirect_stdout)
        return output


CLASS = DummyContainer
