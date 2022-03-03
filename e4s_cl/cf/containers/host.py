"""
Containerless support
"""

import os
import tempfile
from pathlib import Path
from e4s_cl import CONTAINER_SCRIPT
from e4s_cl.util import which, run_subprocess
from e4s_cl.logger import get_logger
from e4s_cl.cf.containers import Container, BackendNotAvailableError
from e4s_cl.cf.libraries import libc_version

LOGGER = get_logger(__name__)

NAME = 'containerless'
MIMES = []


class Containerless(Container):
    """
    Containerless object
    """

    executable_name = 'bash'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.executable = which(self.__class__.executable_name)

        # pylint: disable=R1732
        # The following directory will hold symlinks to the libraries bound to
        # the container; the file will be deleted once the object is deleted
        self._lib_dir = tempfile.TemporaryDirectory()

    @property
    def script(self):
        return Path(self._lib_dir.name, Path(CONTAINER_SCRIPT).name)

    @property
    def import_dir(self):
        return Path(self._lib_dir.name)

    @property
    def import_library_dir(self):
        return Path(self._lib_dir.name, super().import_library_dir.name)

    def get_data(self):
        self.libc_v = libc_version()

        return set()

    def _setup_import(self) -> None:
        """
        Create symlinks to bound libraries in a temporary directory
        """
        for source, destination, _ in self.bound:
            # Abort if not a file
            if not source.resolve().is_file():
                continue

            # Abort if not bound in the special dir
            try:
                rel = destination.relative_to(self.import_dir)
            except ValueError:
                LOGGER.debug("%s is not in %s", destination, self.import_dir)
                continue

            link = Path(self._lib_dir.name, rel)
            os.makedirs(link.parent, exist_ok=True)
            os.symlink(source.resolve(), link)

        ld_path = os.environ.get("LD_LIBRARY_PATH")

        if ld_path:
            ld_path = f"{self._lib_dir.name}{os.pathsep}{ld_path}"
        else:
            ld_path = self._lib_dir.name

        self.env["LD_LIBRARY_PATH"] = ld_path

    def run(self, command):
        """
        def run(self, command: list[str]):
        """

        if not which(self.executable):
            raise BackendNotAvailableError(self.executable)

        self._setup_import()

        return run_subprocess(command, env=self.env)


CLASS = Containerless
