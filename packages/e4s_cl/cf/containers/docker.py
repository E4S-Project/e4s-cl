import sys
import docker
from e4s_cl import logger
from e4s_cl.cf.containers import Container, FileOptions

LOGGER = logger.get_logger(__name__)

NAME = 'docker'
EXECUTABLES = ['docker']
MIMES = []


class DockerContainer(Container):

    def run(self, command: list[str]):
        # Create the client from the environment
        client = docker.from_env()

        # Ensure the queried image is accessible
        try:
            image = client.images.get(self.image)
        except docker.errors.ImageNotFound as err:
            raise BackendError('docker') from err
        except docker.errors.APIError as err:
            raise BackendNotAvailableError('docker') from err

        mounts = list()
        for source, dest, options_val in self.bound:
            mounts.append(
                docker.types.Mount(
                    dest.as_posix(),
                    source.as_posix(),
                    type='bind',
                    read_only=(options_val == FileOptions.READ_ONLY)))

        outlog = client.containers.run(image,
                                       command,
                                       stdout=True,
                                       stderr=True,
                                       mounts=mounts)

        print(outlog.decode(), file=sys.stdout)


CLASS = DockerContainer
