import os
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


class PodmanContainer(Container):
    pipe_manager = NamedPipe

    def _fd_number(self):
        max_good_fd = 2
        fd_number = len(list(Path('/proc/self/fd').glob('*')))
        for fd in range(3, fd_number):
            try:
                os.set_inheritable(fd, True)
            except OSError as err:
                if err.errno != 9:
                    raise InternalError(
                        f"Failed to set the inheritable flag on fd {fd}: {str(err)}"
                    ) from err
            else:
                max_good_fd = fd

        return max_good_fd - 3

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

        return run_subprocess(container_cmd, env=self.env)


CLASS = PodmanContainer
