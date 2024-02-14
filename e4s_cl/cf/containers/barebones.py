"""
Module introducing singularity support
"""

import os
from pathlib import Path
from typing import List, Union, Optional
from e4s_cl import logger, BAREBONES_SCRIPT, BAREBONES_LIBRARY_DIR
from e4s_cl.util import run_subprocess, create_symlink
from e4s_cl.cf.libraries import cache_libraries
from e4s_cl.cf.containers import Container, FileOptions, BackendNotAvailableError

LOGGER = logger.get_logger(__name__)

NAME = 'barebones'
MIMES = []

OPTION_STRINGS = {FileOptions.READ_ONLY: 'ro', FileOptions.READ_WRITE: 'rw'}


class BarebonesContainer(Container):
    """
    Class to use when formatting bound files for a singularity execution
    """

    executable_name = ''

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def _working_dir(self):
        return ['--pwd', os.getcwd()]

    def __setup__(self):
        """
        Bind minimal directories stripped from the use of `--contain`
        """
        # Ensure HOME is bound
        #self.bind_file(Path.home(), option=FileOptions.READ_WRITE)

        # To use with --contain, but removed as it prevented PMI setup on Theta
        #self.bind_file('/dev', option=FileOptions.READ_WRITE)
        #self.bind_file('/tmp', option=FileOptions.READ_WRITE)

    @property
    def script(self):
        return Path(BAREBONES_SCRIPT)

    @property
    def import_library_dir(self):
        return Path(BAREBONES_LIBRARY_DIR)

    def _format_bound(self):
        """
        Format a list of files to a compatible bind option of singularity
        """

        def _format():
            for file in self.bound:
                yield f"{file.origin}:{file.destination}:{OPTION_STRINGS[file.option]}"

        self.env.update({"BAREBONES_BIND": ','.join(_format())})

    def _prepare(self, command: List[str], overload: bool = True) -> List[str]:
        """
        Return the command to run in a list of string
        """
        self.env.update(
            {'BAREBONESENV_LD_PRELOAD': ":".join(self.ld_preload)})

        # LD_LIBRARY_PATH override does not respect container's values.
        # Enabling this may prevent crashes with nvidia library import
        # from singularity (--nv flag) but causes MORE crashes with client containers
        # self.env.update({'SINGULARITYENV_LD_LIBRARY_PATH': ":".join(self.ld_lib_path)})
        self._format_bound()
        nvidia_flag = ['--nv'] if self._has_nvidia() else []

        return [
            *self._additional_options('exec'),
            *command,
        ]

    def bind_file(self,
                  path: Union[Path, str],
                  dest: Optional[Path] = None,
                  option: int = FileOptions.READ_ONLY) -> None:
        """
        This doesn't bind files, but does the equivalent preparation
        of making required files available for the final process to 
        run using them for the barebones container.
        """

        create_symlink(Path(path), Path(BAREBONES_LIBRARY_DIR))


    def bind_env_var(self, key, value):
        self.env.update({f"BAREBONESENV_{key}": value})

    def _has_nvidia(self):
        # Assume that the proper ldconfig call has been run and that nvidia
        # libraries are listed in the cache
        if 'nvidia' not in " ".join(cache_libraries()):
            LOGGER.debug("Disabling Nvidia support: no libraries found")
            return False
        return True

    def run(self, command: List[str], overload: bool = True) -> int:


        container_cmd = [*self._prepare(command, overload)]
        LOGGER.debug("***************************************888")
        LOGGER.debug(container_cmd)
        LOGGER.debug(self.env)
        LOGGER.debug("***************************************888")

        return run_subprocess(container_cmd, env=self.env)


CLASS = BarebonesContainer
