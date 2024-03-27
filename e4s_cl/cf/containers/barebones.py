"""
Module introducing singularity support
"""

import os
from pathlib import Path
from typing import List, Union, Optional
from e4s_cl import logger, BAREBONES_SCRIPT, BAREBONES_LIBRARY_DIR
from e4s_cl.util import run_subprocess, create_symlink, empty_dir, mkdirp, list_directory_files
from e4s_cl.cf.libraries import cache_libraries
from e4s_cl.cf.containers import Container, FileOptions, BackendNotAvailableError
from e4s_cl.cf.wi4mpi import wi4mpi_root

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
        if Path(BAREBONES_LIBRARY_DIR).is_dir():
            empty_dir(Path(BAREBONES_LIBRARY_DIR))
        else:
            mkdirp(Path(BAREBONES_LIBRARY_DIR))
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


    def list_directory_sofiles(self, path: Path):
        """Lists all the so files of a directory.

        Args:
            path (Path): path of the directory list the so files of.

        Returns:
            A list of paths of the so files in the given directory.
        """
        file_paths = list_directory_files(path)
        sofile_paths = []
        for file_path in file_paths:
            if '.so' in file_path.suffixes: # Check if it is a library file
                sofile_paths.append(file_path.absolute())
        return sofile_paths

    def _prepare(self, command: List[str], overload: bool = True) -> List[str]:
        """
        Return the command to run in a list of string
        """

        # Chech the environment for the use of Wi4MPI
        wi4mpi_install_dir = wi4mpi_root()
        # If WI4MPI is to be used, we don't preload the mpi's libraries
        if wi4mpi_install_dir is None:
            to_be_preloaded = self.list_directory_sofiles(Path(BAREBONES_LIBRARY_DIR))
            for file_path in to_be_preloaded:
                self.add_ld_preload(str(file_path))
            self.env.update(
                {'LD_PRELOAD': ":".join(self.ld_preload)})

        # LD_LIBRARY_PATH override does not respect container's values.
        # Enabling this may prevent crashes with nvidia library import
        # from singularity (--nv flag) but causes MORE crashes with client containers
        # self.env.update({'SINGULARITYENV_LD_LIBRARY_PATH': ":".join(self.ld_lib_path)})
        self._format_bound()
        nvidia_flag = ['--nv'] if self._has_nvidia() else []

        return [
            *self._additional_options(),
            *command,
            *self._additional_options('exec'),
        ]

    def bind_file(self,
                  path: Union[Path, str],
                  dest: Optional[Path] = None,
                  option: int = FileOptions.READ_ONLY) -> None:
        """
        This doesn't bind files, but does the equivalent preparation
        of making required files available for the final process to 
        run using them for the barebones container.
        Instead of binding files it creates a symlink of them to a
        specific directory for e4s-cl to find them.
        """
        file_to_bind = Path(path)
        file_basename = file_to_bind.name
        if dest is not None:
            dest = Path(dest)
            if dest.name == 'barebones_script':
                dest.write_text(file_to_bind.read_text())
                os.chmod(dest, 0o755)
            else:
                create_symlink(file_to_bind, Path(dest))
        else:
            create_symlink(file_to_bind, Path(BAREBONES_LIBRARY_DIR) / file_basename)


    def bind_env_var(self, key, value):
        self.env.update({f"{key}": value})

    def _has_nvidia(self):
        # Assume that the proper ldconfig call has been run and that nvidia
        # libraries are listed in the cache
        if 'nvidia' not in " ".join(cache_libraries()):
            LOGGER.debug("Disabling Nvidia support: no libraries found")
            return False
        return True

    def run(self, command: List[str], overload: bool = True) -> int:

        container_cmd = [*self._prepare(command, overload)]

        return run_subprocess(container_cmd, env=self.env)


CLASS = BarebonesContainer
