import os
import sys
import docker
from e4s_cl import logger
from e4s_cl.variables import CHILD_MARKER
from e4s_cl.cf.pipe import ENV_VAR_NAMED, NamedPipe
from e4s_cl.cf.containers import Container, FileOptions

LOGGER = logger.get_logger(__name__)

NAME = 'docker'
EXECUTABLES = ['docker']
MIMES = []



class DockerContainer(Container):
    pipe_manager = NamedPipe

    def run(self, command: list[str]):
        # Create the client from the environment
        client = docker.from_env()

        for variable in [ENV_VAR_NAMED, CHILD_MARKER, logger.LOG_ID_MARKER]:
            if os.environ.get(variable, ''):
                self.bind_env_var(variable, os.environ[variable])

        if os.environ.get(ENV_VAR_NAMED, ''):
            self.bind_file(os.environ[ENV_VAR_NAMED], option=FileOptions.READ_WRITE)

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

        container_env = dict(os.environ)
        for key, val in self.env.items():
            if val is None:
                container_env.pop(key, None)
            else:
                container_env[key] = val

        outlog = client.containers.run(image,
                                       command,
                                       environment=container_env,
                                       stdout=True,
                                       stderr=True,
                                       mounts=mounts)

        print(outlog.decode(), file=sys.stdout)


CLASS = DockerContainer
