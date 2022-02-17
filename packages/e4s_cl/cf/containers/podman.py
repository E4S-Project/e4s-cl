import os
from shlex import join
from pathlib import Path
from e4s_cl.error import InternalError
from e4s_cl.util import which, run_subprocess
from e4s_cl.logger import get_logger
from e4s_cl.cf.pipe import NamedPipe, ENV_VAR_NAMED
from e4s_cl.cf.containers import Container, FileOptions, BackendNotAvailableError

LOGGER = get_logger(__name__)

NAME = 'podman'
EXECUTABLES = ['podman']
MIMES = []


def opened_fds():
    fds = []

    for file in Path('/proc/self/fd').glob('*'):
        if not file.exists():
            continue

        try:
            fd_no = int(file.name)
        except:
            continue

        fds.append(fd_no)

    return fds


class FDFiller:

    def __init__(self):
        self.__opened_files = []

    def __enter__(self):
        fds = opened_fds()

        for fd in fds:
            try:
                os.set_inheritable(fd, True)
            except OSError as err:
                if err.errno == 9:
                    continue

        missing = set(range(max(fds))) - set(fds)

        while missing:
            null = open('/dev/null', 'w')

            if null.fileno() not in missing:
                raise InternalError(f"Unexpected fileno: {null.fileno()}")

            try:
                os.set_inheritable(null.fileno(), True)
            except OSError as err:
                if err.errno == 9:
                    continue

            missing.discard(null.fileno())

            self.__opened_files.append(null)
        LOGGER.debug("Created %d file descriptors: %s",
                     len(self.__opened_files),
                     [f.fileno() for f in self.__opened_files])

    def __exit__(self, type_, value, traceback):
        for file in self.__opened_files:
            file.close()


class PodmanContainer(Container):
    pipe_manager = NamedPipe

    def _fd_number(self):
        """
        Podman requires the --preserve-fds=K option to pass file descriptors;
        K being the amount (in addition of 0,1,2) of fds to pass. It also is
        strict on the inheritance flag of those descriptors, and will not
        function if any one of them is invalid/uninheritable. To abide to this,
        we go through all the opened file descriptors, manually set the 
        inheritance flag to true, and return as soon as a file descriptor refuses
        """

        LOGGER.debug("Max fd: %d (%s)", max(opened_fds()), opened_fds())
        return max(opened_fds()) - 3

    def _working_dir(self):
        return ['--workdir', os.getcwd()]

    def _format_bound(self):

        def _format():
            fifo = os.environ.get(ENV_VAR_NAMED, '')
            if fifo:
                yield f"--mount=type=bind,src={fifo},dst={fifo},ro=false"

            for src, dst, opt in self.bound:
                yield f"--mount=type=bind,src={src.as_posix()},dst={dst.as_posix()}{',ro=true' if (opt == FileOptions.READ_ONLY) else ''}"

        return list(_format())

    def _prepare(self, command):

        return [
            self.executable,  # absolute path to podman
            'run',  # Run a container
            '--rm',  # Remove when done
            '--ipc=host',  # Use host IPC /!\
            '--env-host',  # Pass host environment /!\
            f"--preserve-fds={self._fd_number()}",  # Inherit file descriptors /!\
            *self._working_dir(),  # Work in the same CWD
            *self._format_bound(),  # Bound files options
            self.image,
            *command
        ]

    def run(self, command):
        """
        def run(self, command: list[str]):
        """

        if not which(self.executable):
            raise BackendNotAvailableError(self.executable)

        container_cmd = self._prepare(command)

        with FDFiller():
            return run_subprocess(container_cmd, env=self.env)


CLASS = PodmanContainer
