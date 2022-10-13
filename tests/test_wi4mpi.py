import tests
import shlex
from pathlib import Path
from tempfile import TemporaryDirectory, NamedTemporaryFile
from e4s_cl.cf.detect_mpi import MPIIdentifier
from e4s_cl.cf.wi4mpi import (wi4mpi_adapt_arguments)
from e4s_cl.cf.wi4mpi.install import (WI4MPI_RELEASE_URL, _download_wi4mpi,
                                      _update_config)


class Wi4MPITest(tests.TestCase):

    def test_update_config(self):
        with NamedTemporaryFile(mode='w', delete=False) as config:
            config_file = config.name
            config.write("MPICH_DEFAULT_ROOT=\"path/to/installation\"")

        _update_config(config_file, 'MPICH_DEFAULT_ROOT', 'new/value')
        _update_config(config_file, 'OPENMPI_DEFAULT_ROOT', 'other/value')

        with open(config_file, 'r') as config:
            data = config.read()

            self.assertIn('MPICH_DEFAULT_ROOT="new/value"', data)
            self.assertIn('OPENMPI_DEFAULT_ROOT="other/value"', data)

        Path(config_file).unlink()

    def test_adapt_arguments(self):
        command = shlex.split(
            "mpirun -np 4 -T mpich -F openmpi --mca btl_tcp_if_include ib0 -x PATH"
        )
        converted = wi4mpi_adapt_arguments(command)
        self.assertEqual(
            converted,
            shlex.split(
                "mpirun -T mpich -F openmpi -E \"-np 4 --mca btl_tcp_if_include ib0 -x PATH\""
            ))

        command = shlex.split("mpirun -T mpich -F openmpi")
        converted = wi4mpi_adapt_arguments(command)
        self.assertEqual(converted, shlex.split("mpirun -T mpich -F openmpi"))

        command = shlex.split("mpirun -np 4 --mca param value")
        converted = wi4mpi_adapt_arguments(command)
        self.assertEqual(converted,
                         shlex.split("mpirun -E '-np 4 --mca param value'"))
