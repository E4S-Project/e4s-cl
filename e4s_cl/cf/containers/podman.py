"""
Podman container manager support
"""

import os
from pathlib import Path
from typing import List
from e4s_cl.error import InternalError
from e4s_cl.util import run_subprocess
from e4s_cl.logger import get_logger
from e4s_cl.cf.containers import Container, FileOptions, BackendNotAvailableError

LOGGER = get_logger(__name__)

NAME = 'podman'
MIMES = []


def opened_fds():
    """
    -> set[int]

    Returns a list of all the opened file descriptors opened by the current
    process
    """
    fds = set()

    for file in Path('/proc/self/fd').glob('*'):
        if not file.exists():
            continue

        try:
            fd_no = int(file.name)
        except ValueError:
            continue

        fds.add(fd_no)

    return fds


class FDFiller:
    """
    Context manager that will "fill" the opened file descriptors to have a
    contiguous list, and make every fd inheritable
    """

    def __init__(self):
        """
        Initialize by creating a buffer of opened files
        """
        self.__opened_files = []

    def __enter__(self):
        """
        Create as many open files as necessary
        """
        fds = opened_fds()

        # Make every existing file descriptor inheritable
        for fd in fds:
            try:
                os.set_inheritable(fd, True)
            except OSError as err:
                if err.errno == 9:
                    continue

        # Compute all the missing numbers in the list
        missing = set(range(max(fds))) - set(fds)

        while missing:
            # Open files towards /dev/null
            null = open('/dev/null', 'w', encoding='utf-8')

            if null.fileno() not in missing:
                raise InternalError(f"Unexpected fileno: {null.fileno()}")

            try:
                # Set the file as inheritable
                os.set_inheritable(null.fileno(), True)
            except OSError as err:
                if err.errno == 9:
                    continue

            # It is not missing anymore
            missing.discard(null.fileno())
            self.__opened_files.append(null)

        passed_fds = fds - {0, 1, 2}
        LOGGER.debug("Passing %d file descriptors: (%s)", len(passed_fds), passed_fds)
        LOGGER.debug("Created %d file descriptors: %s",
                     len(self.__opened_files),
                     [f.fileno() for f in self.__opened_files])

    def __exit__(self, type_, value, traceback):
        for file in self.__opened_files:
            file.close()


class PodmanContainer(Container):
    """
    Podman container object
    """

    executable_name = 'podman'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def _fd_number(self):
        """
        -> int
        Podman requires the --preserve-fds=K option to pass file descriptors;
        K being the amount (in addition of 0,1,2) of fds to pass. It also is
        strict on the existence and inheritance flag of those descriptors, and
        will not function if any one of them is invalid/uninheritable.
        """

        fds = opened_fds() - {0, 1, 2}

        return len(fds)

    def _format_bound(self):

        def _format():
            for file in self.bound:
                params = {
                    'type': 'bind',
                    'src': file.origin.as_posix(),
                    'dst': file.destination.as_posix(),
                }

                if file.option == FileOptions.READ_ONLY:
                    params['ro'] = 'true'

                yield "--mount=" + ",".join(f"{k}={v}"
                                            for (k, v) in params.items())

        return list(_format())

    def _prepare(self, command: List[str], overload: bool = True) -> List[str]:
        """
        Prepare a command line to run the given command in a podman container
        """

        def _working_dir() -> List[str]:
            cwd = os.getcwd()
            if cwd in map(lambda x: x.origin, self.bound):
                return ['--workdir', cwd]
            return []

        if overload:
            podman_command = [
                *self._additional_options(),  # Additional options
                'run',  # Run a container
                '--rm',  # Remove when done
                '--ipc=host',  # Use host IPC /!\
                '--env-host',  # Pass host environment /!\
                f"--preserve-fds={self._fd_number()}",  # Inherit file descriptors /!\
                *_working_dir(),  # Work in the same CWD
                *self._format_bound(),  # Bound files options
                *self._additional_options('run'),  # Additional run options
                self.image,
                *command,
            ]
        else:
            podman_command = [
                'run',  # Run a container
                '--rm',  # Remove when done
                f"--preserve-fds={self._fd_number()}",  # Inherit file descriptors /!\
                self.image,
                *command,
            ]

        return podman_command

    def run(self, command: List[str], overload: bool = True) -> int:
        executable = self._executable()
        if executable is None:
            raise BackendNotAvailableError(self.__class__.__name__)

        with FDFiller():
            container_cmd = [executable, *self._prepare(command, overload)]
            return run_subprocess(container_cmd, env=self.env)


CLASS = PodmanContainer
