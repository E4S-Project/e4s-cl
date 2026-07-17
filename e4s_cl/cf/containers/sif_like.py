"""
Shared implementation for singularity/apptainer style backends.
"""

import os
from pathlib import Path
from typing import List

from e4s_cl import logger
from e4s_cl.util import run_subprocess
from e4s_cl.cf.libraries import cache_libraries
from e4s_cl.cf.containers import Container, FileOptions, BackendNotAvailableError

LOGGER = logger.get_logger(__name__)

# Internal shared module (not a user-selectable backend)
NAME = '_sif_like'
CLASS = None
DEBUG_BACKEND = True

OPTION_STRINGS = {FileOptions.READ_ONLY: 'ro', FileOptions.READ_WRITE: 'rw'}


class SifLikeContainer(Container):
    """Common behavior for singularity-like runtimes."""

    bind_env_var_name = ''
    env_prefix = ''
    export_ld_library_path = False

    def _working_dir(self):
        return ['--pwd', os.getcwd()]

    def __setup__(self):
        """
        Bind minimal directories stripped from the use of `--contain`
        """
        self.bind_file(Path.home(), option=FileOptions.READ_WRITE)

    def _format_bound(self):
        """Format bound files for singularity/apptainer bind env variable."""

        def _format():
            for file in self.bound:
                yield f"{file.origin}:{file.destination}:{OPTION_STRINGS[file.option]}"

        self.env.update({self.bind_env_var_name: ','.join(_format())})

    def _prepare(self, command: List[str], overload: bool = True) -> List[str]:
        """Return the command to run in a list of strings."""
        # As of mid-2022, apptainer still uses the `.singularity.d` folder.
        self.add_ld_library_path("/.singularity.d/libs")
        self.env.update({
            f"{self.env_prefix}_LD_PRELOAD": ":".join(self.ld_preload),
        })

        if self.export_ld_library_path:
            self.env.update({
                f"{self.env_prefix}_LD_LIBRARY_PATH": ":".join(self.ld_lib_path),
            })

        self._format_bound()
        nvidia_flag = ['--nv'] if self._has_nvidia() else []

        return [
            *self._additional_options(),
            'exec',
            *self._working_dir(),
            *nvidia_flag,
            *self._additional_options('exec'),
            self.image,
            *command,
        ]

    def bind_env_var(self, key, value):
        self.env.update({f"{self.env_prefix}_{key}": value})

    def _has_nvidia(self):
        # Assume that the proper ldconfig call has been run and that nvidia
        # libraries are listed in the cache.
        if 'nvidia' not in " ".join(cache_libraries()):
            LOGGER.debug("Disabling Nvidia support: no libraries found")
            return False
        return True

    def run(self, command: List[str], overload: bool = True) -> int:
        executable = self._executable()
        if executable is None:
            raise BackendNotAvailableError(self.__class__.__name__)

        container_cmd = [executable, *self._prepare(command, overload)]

        return run_subprocess(container_cmd, env=self.env)
