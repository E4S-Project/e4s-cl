"""
Module introducing singularity support
"""

import os
from pathlib import Path
from e4s_cl import logger
from e4s_cl.util import which, run_subprocess
from e4s_cl.cf.libraries import host_libraries
from e4s_cl.cf.containers import Container, FileOptions, BackendNotAvailableError
from e4s_cl.config import configuration

LOGGER = logger.get_logger(__name__)

NAME = 'singularity'
MIMES = ['.simg', '.sif']

OPTION_STRINGS = {FileOptions.READ_ONLY: 'ro', FileOptions.READ_WRITE: 'rw'}

class SingularityContainer(Container):
    """
    Class to use when formatting bound files for a singularity execution
    """

    executable_name = 'singularity'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.executable = which(self.__class__.executable_name)

    def _working_dir(self):
        return ['--pwd', os.getcwd()]

    def __setup__(self):
        """
        Bind minimal directories stripped from the use of `--contain`
        """
        # Ensure HOME is bound
        self.bind_file(Path.home(), option=FileOptions.READ_WRITE)

        # To use with --contain, but removed as it prevented PMI setup on Theta
        #self.bind_file('/dev', option=FileOptions.READ_WRITE)
        #self.bind_file('/tmp', option=FileOptions.READ_WRITE)

    def _format_bound(self):
        """
        Format a list of files to a compatible bind option of singularity
        """

        def _format():
            for source, dest, options_val in self.bound:
                yield f"{source}:{dest}:{OPTION_STRINGS[options_val]}"

        self.env.update({"SINGULARITY_BIND": ','.join(_format())})

    def _prepare(self, command):
        """
        -> list[str]

        Return the command to run in a list of string
        """
        self.add_ld_library_path("/.singularity.d/libs")
        self.env.update(
            {'SINGULARITYENV_LD_PRELOAD': ":".join(self.ld_preload)})
        self.env.update(
            {'SINGULARITYENV_LD_LIBRARY_PATH': ":".join(self.ld_lib_path)})
        self._format_bound()
        nvidia_flag = ['--nv'] if self._has_nvidia() else []

        # Check for additional options in config files
        config = configuration.options('SINGULARITY_OPTIONS', 'cli_options'),
        additional_options = []
        if config is not None:
            additional_options = config

        return [
            self.executable, 'exec',
            *additional_options,
            *self._working_dir(), *nvidia_flag, self.image, *command
        ]

    def bind_env_var(self, key, value):
        self.env.update({f"SINGULARITYENV_{key}": value})

    def _has_nvidia(self):
        if 'nvidia' not in " ".join(host_libraries()):
            LOGGER.debug("Disabling Nvidia support: no libraries found")
            return False
        return True

    def run(self, command):
        if not self.executable:
            raise BackendNotAvailableError(self.executable)

        container_cmd = self._prepare(command)

        return run_subprocess(container_cmd, env=self.env)


CLASS = SingularityContainer
