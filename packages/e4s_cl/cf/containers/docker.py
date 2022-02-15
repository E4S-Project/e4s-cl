"""
Module introducing docker backend support
"""

import os
import sys
import docker
from e4s_cl.logger import get_logger
from e4s_cl.cf.pipe import ENV_VAR_NAMED, NamedPipe
from e4s_cl.cf.containers import Container, FileOptions, BackendError, BackendNotAvailableError

LOGGER = get_logger(__name__)

NAME = 'docker'
EXECUTABLES = ['docker']
MIMES = []


class DockerContainer(Container):
    """
    Class used to abstract docker containers
    """
    pipe_manager = NamedPipe

    def run(self, command):
        """
        def run(self, command: list[str]):
        """

        # Create the client from the environment
        client = docker.from_env()

        # Ensure the queried image is accessible
        try:
            image = client.images.get(self.image)
        except docker.errors.ImageNotFound as err:
            raise BackendError('docker') from err
        except docker.errors.APIError as err:
            raise BackendNotAvailableError('docker') from err

        mounts = []
        for source, dest, options_val in self.bound:
            mounts.append(
                docker.types.Mount(
                    dest.as_posix(),
                    source.as_posix(),
                    type='bind',
                    read_only=(options_val == FileOptions.READ_ONLY)))

        fifo = os.environ.get(ENV_VAR_NAMED, '')
        if fifo:
            mounts.append(
                docker.types.Mount(fifo, fifo, type='bind', read_only=False))

        container_env = dict(os.environ)
        for key, val in self.env.items():
            if val is None:
                container_env.pop(key, None)
            else:
                container_env[key] = val

        try:
            outlog = client.containers.run(image,
                                           command,
                                           environment=container_env,
                                           stdout=True,
                                           stderr=True,
                                           mounts=mounts,
                                           remove=True)
        except docker.errors.ImageNotFound as err:
            raise BackendError('docker') from err
        except docker.errors.APIError as err:
            raise BackendNotAvailableError('docker') from err
        except docker.errors.ContainerError as err:
            LOGGER.error("Process in container %s failed with code %d:",
                         err.container.short_id, err.exit_status)
            for line in err.stderr.decode().split("\n"):
                LOGGER.error(line)
            return err.exit_status
        else:
            print(outlog.decode(), file=sys.stdout, end='')

        return 0


CLASS = DockerContainer
