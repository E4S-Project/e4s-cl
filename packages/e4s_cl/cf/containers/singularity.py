"""
Module introducing singularity support
"""

from e4s_cl import logger
from e4s_cl.util import create_subprocess_exp
from e4s_cl.cf.libraries import host_libraries
from e4s_cl.cf.containers import Container

LOGGER = logger.get_logger(__name__)

NAME = 'singularity'
EXECUTABLES = ['singularity']
MIMES = ['.simg', '.sif']


class SingularityContainer(Container):
    """
    Class to use when formatting bound files for a singularity execution
    """
    def run(self, command, redirect_stdout=False):
        self.add_ld_library_path("/.singularity.d/libs")
        self.env.update(
            {'SINGULARITYENV_LD_PRELOAD': ":".join(self.ld_preload)})
        self.env.update(
            {'SINGULARITYENV_LD_LIBRARY_PATH': ":".join(self.ld_lib_path)})
        self.format_bound()
        nvidia_flag = ['--nv'] if self._has_nvidia() else []
        container_cmd = [self.executable, 'exec'
                         ] + nvidia_flag + [self.image.as_posix()] + command

        return create_subprocess_exp(container_cmd,
                                     env=self.env,
                                     redirect_stdout=redirect_stdout)

    def format_bound(self):
        """
        Format a list of files to a compatible bind option of singularity
        """
        file_list = []

        for request in self.bound:
            if request[1]:
                file_list.append("%s:%s:%s" % request)
            else:
                file_list.append("%s:%s:%s" %
                                 (request[0], request[0], request[2]))

        files = ','.join(file_list)

        if files:
            self.env.update({"SINGULARITY_BIND": files})

    def bind_env_var(self, key, value):
        new_key = "SINGULARITYENV_{}".format(key)
        self.env.update({new_key: value})

    def _has_nvidia(self):
        if 'nvidia' not in " ".join(host_libraries().keys()):
            LOGGER.debug("Disabling Nvidia support: no libraries found")
            return False
        return True


CLASS = SingularityContainer
