import os
import subprocess
import tarfile
import urllib.request
from pathlib import Path
from tempfile import NamedTemporaryFile
from e4s_cl import E4S_CL_HOME
from e4s_cl.util import safe_tar
from e4s_cl.logger import get_logger
from e4s_cl.cf.detect_name import _get_mpi_vendor_version, filter_mpi_libs

LOGGER = get_logger(__name__)

WI4MPI_RELEASE_URL = 'https://github.com/cea-hpc/wi4mpi/archive/refs/tags/v3.6.1.tar.gz'

WI4MPI_DIR = Path(E4S_CL_HOME) / "wi4mpi"


def _install_wi4mpi():
    return install_wi4mpi()


def _nop():
    pass


DISTRO_DICT = {
    'Intel(R) MPI': _nop,
    'Open MPI': _install_wi4mpi,
    'Spectrum MPI': _nop,
    'CRAY MPICH': _nop,
    'MPICH': _nop,
    'MVAPICH': _nop
}


def check_wi4mpi(profile):
    """
    Checks if the mpi vendor detected needs wi4mpi in order to function
    correctly with e4s-cl, and if so installs it.
    """
    installed = False
    mpi_libs = filter_mpi_libs(profile)
    vendor_list = list(filter(None, map(_get_mpi_vendor_version, mpi_libs)))
    if vendor_list:
        vendor = vendor_list[0][0]
        installed = DISTRO_DICT.get(vendor)()
    return installed


def download_wi4mpi(url: str, destination: Path) -> bool:
    """
    Download and extract the TAR archive from 'url' into the directory 'destination'
    """
    with urllib.request.urlopen(url) as request:
        if not request.status == 200:
            LOGGER.error("Failed to download Wi4MPI release; aborting")
            return False

        with NamedTemporaryFile(delete=False) as buffer:
            buffer.write(request.read())
            archive = buffer.name

    if not tarfile.is_tarfile(archive):
        LOGGER.error("Downloaded file is not an archive; aborting")
        return False

    with tarfile.open(archive) as data:
        if not safe_tar(data):
            LOGGER.error("Unsafe paths detected in archive; aborting")
            return False

        data.extractall(destination)

    try:
        Path(archive).unlink()
    except OSError as err:
        LOGGER.error("Failed to delete downloaded data: %s", str(err))

    return True


def install_wi4mpi() -> bool:
    """Clones and installs wi4mpi from git run
    
    Installs in ~/.local/share/wi4mpi using a GNU compiler
    """
    build_dir = WI4MPI_DIR / 'build'
    cmakeCmd = ['cmake', \
            '-DCMAKE_INSTALL_PREFIX=~/.local/wi4mpi', \
            '-DWI4MPI_COMPILER=GNU', '..']
    makeCmd = ['make', '-j', '4']
    makeInstallCmd = ['make', 'install']

    def _run_wi4mpi_install_cmd(cmd):
        with subprocess.Popen(cmd) as proc:
            if proc.wait():
                LOGGER.warning(
                    "Wi4mpi installation failed. Proceeding with profile initialisation"
                )
                return False
            return True

    if not download_wi4mpi(WI4MPI_RELEASE_URL, WI4MPI_DIR):
        LOGGER.error("Failed to access Wi4MPI release")
        return False

    try:
        build_dir.mkdir(exist_ok=True)
        os.chdir(build_dir)
    except PermissionError as err:
        LOGGER.debug("Failed to create directory %s: %s", build_dir.as_posix(),
                     str(err))
        nofail = False
        return nofail

    if nofail and not os.path.exists(build_dir / "Makefile"):
        nofail = _run_wi4mpi_install_cmd(cmakeCmd)

    if nofail and not os.path.exists(build_dir / "install_manifest.txt"):
        nofail = _run_wi4mpi_install_cmd(makeCmd)
        if nofail:
            nofail = _run_wi4mpi_install_cmd(makeInstallCmd)

    if nofail:
        LOGGER.warning("Wi4MPI is built and installed")

    return nofail
