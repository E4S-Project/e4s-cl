import os
import sys
import subprocess
from e4s_cl import logger
from e4s_cl.util import which, create_subprocess_exp, _ldd_output_parser
from e4s_cl.cf.containers import Container

LOGGER = logger.get_logger(__name__)

class SingularityContainer(Container):
    def run(self, command, redirect_stdout=False):
        container_cmd = [which('singularity'), 'exec', '--nv'] + self.format_bound() + [self.image.as_posix()] + command
        retval, output = create_subprocess_exp(container_cmd, env=self.env, redirect_stdout=redirect_stdout)
        return output

    def format_bound(self):
        fileList = ["{}:{}:{}".format(*request) for request in self.bound]
        files = ','.join(fileList)
        if files:
            return ['-B', files]
        return []

    def bind_env_var(self, key, value):
        new_key = "SINGULARITYENV_{}".format(key)
        self.env.update({new_key: value})

    @staticmethod
    def is_available():
        return which('singularity') != None

MIMES = ['simg']
AVAILABLE = SingularityContainer.is_available()
CLASS = SingularityContainer
