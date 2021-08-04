"""
Module introducing singularity support
"""

from pathlib import Path
from e4s_cl import logger
from e4s_cl.util import create_subprocess_exp
from e4s_cl.cf.libraries import host_libraries
from e4s_cl.cf.containers import Container, FileOptions

LOGGER = logger.get_logger(__name__)

NAME = 'singularity'
EXECUTABLES = ['singularity']
MIMES = ['.simg', '.sif']

OPTION_STRINGS = {FileOptions.READ_ONLY: 'ro', FileOptions.READ_WRITE: 'rw'}


class SingularityContainer(Container):
    """
    Class to use when formatting bound files for a singularity execution
    """

    def __setup__(self):
        """
        Bind minimal directories stripped from the use of `--contain`
        """
        self.bind_file(Path.home(), option=FileOptions.READ_WRITE)
        self.bind_file('/dev', option=FileOptions.READ_WRITE)
        self.bind_file('/tmp', option=FileOptions.READ_WRITE)

    def run(self, command, redirect_stdout=False):
        self.add_ld_library_path("/.singularity.d/libs")
        self.env.update(
            {'SINGULARITYENV_LD_PRELOAD': ":".join(self.ld_preload)})
        self.env.update(
            {'SINGULARITYENV_LD_LIBRARY_PATH': ":".join(self.ld_lib_path)})
        self.format_bound()
        nvidia_flag = ['--nv'] if self._has_nvidia() else []
        container_cmd = [self.executable, 'exec', '--contain'
                         ] + nvidia_flag + [self.image] + command

        return create_subprocess_exp(container_cmd,
                                     env=self.env,
                                     redirect_stdout=redirect_stdout)

    def format_bound(self):
        """
        Format a list of files to a compatible bind option of singularity
        """
        def _format():
            for source, dest, options_val in self.bound:
                yield "%s:%s:%s" % (source, dest, OPTION_STRINGS[options_val])

        self.env.update({"SINGULARITY_BIND": ','.join(_format())})

    def bind_env_var(self, key, value):
        new_key = "SINGULARITYENV_{}".format(key)
        self.env.update({new_key: value})

    def _has_nvidia(self):
        if 'nvidia' not in " ".join(host_libraries().keys()):
            LOGGER.debug("Disabling Nvidia support: no libraries found")
            return False
        return True


CLASS = SingularityContainer
