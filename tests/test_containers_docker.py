from pathlib import Path
import sys
import shlex
import docker
import tests
from e4s_cl.cf.containers import Container, BackendError
from e4s_cl.cf.containers.docker import DockerContainer
from tempfile import TemporaryFile

__IMAGE__ = "centos:7"

try:
    client = docker.from_env()
    try:
        client.images.get(__IMAGE__)
    except BackendError as err:
        IMAGE_AVAIL = False
    else:
        IMAGE_AVAIL = True
    DOCKER_AVAIL = True
except docker.errors.DockerException:
    DOCKER_AVAIL = False
    IMAGE_AVAIL = False

@tests.skipUnless(DOCKER_AVAIL, "Failed to connect to the docker daemon")
class DockerContainerTest(tests.TestCase):

    def test_create(self):
        container = Container(name='docker', image=__IMAGE__)
        self.assertFalse(type(container) == Container)
        self.assertTrue(type(container) == DockerContainer)
        self.assertTrue(isinstance(container, Container))

    @tests.skipUnless(IMAGE_AVAIL, f"Image {__IMAGE__} not available")
    def test_run(self):
        container = Container(name='docker', image=__IMAGE__)
        container.run(shlex.split("ls"))

    @tests.skipUnless(IMAGE_AVAIL, f"Image {__IMAGE__} not available")
    def test_run_bound_files(self):
        container = Container(name='docker', image=__IMAGE__)

        returncode = container.run(shlex.split("ls /e4s-cl/tests"))
        self.assertNotEqual(returncode, 0)

        container.bind_file(Path(__file__).parent, dest='/e4s-cl/tests')
        returncode = container.run(shlex.split("ls /e4s-cl/tests"))

        self.assertEqual(returncode, 0)

    @tests.skipUnless(IMAGE_AVAIL, f"Image {__IMAGE__} not available")
    def test_run_bound_env(self):
        container = Container(name='docker', image=__IMAGE__)
        bkpstream = sys.stdout
        sys.stdout = TemporaryFile(mode="w+")

        container.bind_env_var("MYVAR", "MYVALUE")
        container.run(shlex.split("env"))
        sys.stdout.seek(0, 0)
        self.assertIn("MYVALUE", sys.stdout.read())

        sys.stdout = bkpstream

    def test_run_bad_image(self):
        container = Container(name='docker', image='sike_not_an_image')
        with self.assertRaises(BackendError):
            container.run(shlex.split("ls"))
