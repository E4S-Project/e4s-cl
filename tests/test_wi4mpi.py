import tests
from pathlib import Path
from tempfile import TemporaryDirectory, NamedTemporaryFile
from e4s_cl.cf.detect_mpi import MPIIdentifier
from e4s_cl.cf.wi4mpi.install import (WI4MPI_RELEASE_URL, requires_wi4mpi,
                                      _download_wi4mpi, _update_config)


class Wi4MPITest(tests.TestCase):

    def test_require(self):
        self.assertTrue(requires_wi4mpi(MPIIdentifier('Open MPI', 'v0.0.0')))
        self.assertFalse(requires_wi4mpi(MPIIdentifier('Open PI', 'v0.0.0')))
        self.assertFalse(requires_wi4mpi(None))

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
