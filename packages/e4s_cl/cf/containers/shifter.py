"""
Module introducing shifter support
"""

import os
import tempfile
from shutil import copy2, copytree
from pathlib import Path
from e4s_cl import logger, CONTAINER_DIR
from e4s_cl.util import create_subprocess_exp
from e4s_cl.cf.libraries import host_libraries
from e4s_cl.cf.containers import Container, FileOptions

LOGGER = logger.get_logger(__name__)

NAME = 'shifter'
EXECUTABLES = ['shifter']
MIMES = []

OPTION_STRINGS = {FileOptions.READ_ONLY: 'ro', FileOptions.READ_WRITE: 'rw'}


class ShifterContainer(Container):
    """
    Class to use for a shifter execution
    """
    def __setup__(self):
        pass

    def __setup_import(self) -> str:
        """
        Create a temporary directory to bind /.e4s-cl files in
        """

        self.__shifter_e4s_dir = tempfile.TemporaryDirectory()
        LOGGER.debug("Generating import template in '%s'",
                     self.__shifter_e4s_dir.name)

        for source, destination, options in self.bound:
            if destination.as_posix().startswith(CONTAINER_DIR):
                temporary = Path(self.__shifter_e4s_dir.name, destination.name)
                if source.is_dir():
                    copy_op = copytree(source,
                                       temporary,
                                       symlinks=True,
                                       ignore_dangling_symlinks=False,
                                       dirs_exist_ok=True)
                if source.is_file():
                    copy_op = copy2(source, temporary)

        return '--volume=%s:%s' % (self.__shifter_e4s_dir.name, CONTAINER_DIR)

    def run(self, command, redirect_stdout=False):
        env_list = []
        if self.ld_preload:
            env_list.append('--env=LD_PRELOAD=%s' % ":".join(self.ld_preload))
        if self.ld_lib_path:
            env_list.append('--env=LD_LIBRARY_PATH=%s' %
                            ":".join(self.ld_lib_path))

        for env_var in self.env.items():
            env_list.append('--env=%s=%s' % env_var)

        container_cmd = [
            self.executable,
            "--image=%s" % self.image, *env_list,
            self.__setup_import(), *command
        ]
        return create_subprocess_exp(container_cmd,
                                     env=self.env,
                                     redirect_stdout=redirect_stdout)


CLASS = ShifterContainer
