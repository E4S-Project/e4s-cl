import os
import subprocess
from subprocess import DEVNULL, STDOUT
import tarfile
import urllib.request
from pathlib import Path
from typing import Optional
from tempfile import NamedTemporaryFile
from e4s_cl import E4S_CL_HOME
from e4s_cl.util import safe_tar
from e4s_cl.logger import get_logger
from e4s_cl.util import which
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


def download_wi4mpi(url: str, destination: Path) -> Optional[Path]:
    """
    Download and extract the TAR archive from 'url' into the directory 'destination'
    """
    with urllib.request.urlopen(url) as request:
        if not request.status == 200:
            LOGGER.error("Failed to download Wi4MPI release; aborting")
            return None

        with NamedTemporaryFile(delete=False) as buffer:
            buffer.write(request.read())
            archive = buffer.name

    if not tarfile.is_tarfile(archive):
        LOGGER.error("Downloaded file is not an archive; aborting")
        return None

    with tarfile.open(archive) as data:
        if not safe_tar(data):
            LOGGER.error("Unsafe paths detected in archive; aborting")
            return None

        data.extractall(destination)

        release_root_dir = min(data.getnames())

    try:
        Path(archive).unlink()
    except OSError as err:
        LOGGER.error("Failed to delete downloaded data: %s", str(err))

    return destination / release_root_dir


def install_wi4mpi() -> bool:
    """Clones and installs wi4mpi from git run
    
    Installs in ~/.local/share/wi4mpi using a GNU compiler
    """

    if not which("cmake"):
        LOGGER.warning(
            "WI4MPI installation failed: cmake is missing. Proceeding with profile initialisation"
        )
        return False

    def _run_wi4mpi_install_cmd(cmd, discard_output=True):

        stdout = None
        stderr = None
        if discard_output:
            stdout = DEVNULL
            stderr = STDOUT

        with subprocess.Popen(cmd, stdout=stdout, stderr=stderr) as proc:
            if proc.wait():
                if discard_output:
                    LOGGER.warning("WI4MPI installation failed. Retrying")
                    nofail = _run_wi4mpi_install_cmd(cmd, discard_output=False)
                if not nofail:
                    LOGGER.warning(
                        "WI4MPI installation failed. Proceeding with profile initialisation"
                    )
                    return False
            return True

    build_dir = WI4MPI_DIR / 'build'
    source_dir = download_wi4mpi(WI4MPI_RELEASE_URL, WI4MPI_DIR)
    if source_dir is None:
        LOGGER.error("Failed to access Wi4MPI release")
        return False

    nofail = True

    cmakeCmd = [
        'cmake', \
        '-DCMAKE_INSTALL_PREFIX=~/.local/wi4mpi', \
        '-DWI4MPI_COMPILER=GNU', \
        source_dir.as_posix()
    ]
    makeCmd = ['cmake', '--build', '.', '--parallel', '-t', 'install']
    makeInstallCmd = ['make', 'install']

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
        LOGGER.warning("Installing WI4MPI")
        nofail = _run_wi4mpi_install_cmd(makeCmd)
        #if nofail:
        #   nofail = _run_wi4mpi_install_cmd(makeInstallCmd)

    if nofail:
        LOGGER.warning(f"WI4MPI is built and installed")

    return nofail
