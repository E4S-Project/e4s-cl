"""
Containerless support
"""

import os
import tempfile
from pathlib import Path
from e4s_cl import CONTAINER_DIR
from e4s_cl.error import InternalError
from e4s_cl.util import which, run_subprocess
from e4s_cl.logger import get_logger
from e4s_cl.cf.version import Version
from e4s_cl.cf.pipe import NamedPipe, ENV_VAR_NAMED
from e4s_cl.cf.containers import Container, FileOptions, BackendNotAvailableError
from e4s_cl.cf.libraries import LibrarySet

LOGGER = get_logger(__name__)

NAME = 'containerless'
EXECUTABLES = ['bash']
MIMES = []


class Containerless(Container):
    """
    Containerless object
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # The following directory will hold symlinks to the libraries bound to
        # the container; the file will be deleted once the object is deleted
        self._lib_dir = tempfile.TemporaryDirectory()

    def get_data(self, entrypoint, library_set=LibrarySet()):
        self.libc_v = Version('0.0.0')
        self.libraries = LibrarySet(set())

        return self.libraries

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
                rel = destination.relative_to(CONTAINER_DIR)
            except ValueError:
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
