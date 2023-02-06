"""
Module introducing docker backend support
"""

import os
import sys
from typing import List

try:
    import docker
    DOCKER_MODULE = True
except ModuleNotFoundError:
    DOCKER_MODULE = False

from e4s_cl.logger import get_logger
from e4s_cl.cf.containers import Container, FileOptions, BackendError, BackendNotAvailableError

LOGGER = get_logger(__name__)

NAME = 'docker'
EXECUTABLES = ['docker']
MIMES = []


class DockerContainer(Container):
    """
    Class used to abstract docker containers
    """

    def run(self, command: List[str], overload: bool = True) -> int:
        if not DOCKER_MODULE:
            raise BackendNotAvailableError(
                'Docker module required but not found !')

        # Create the client from the environment
        client = docker.from_env()

        # Ensure the queried image is accessible
        try:
            image = client.images.get(self.image)
        except docker.errors.ImageNotFound as err:
            client.close()
            raise BackendError('docker') from err
        except docker.errors.APIError as err:
            client.close()
            raise BackendNotAvailableError('docker') from err

        mounts = []
        for file in self.bound:
            mounts.append(
                docker.types.Mount(
                    file.destination.as_posix(),
                    file.origin.as_posix(),
                    type='bind',
                    read_only=(file.option == FileOptions.READ_ONLY)))

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
        finally:
            client.close()

        return 0


CLASS = DockerContainer
