import os
import subprocess
from shutil import rmtree
from subprocess import DEVNULL, STDOUT
import tarfile
import urllib.request
from pathlib import Path
from typing import Optional
from tempfile import NamedTemporaryFile
from e4s_cl import E4S_CL_HOME
from e4s_cl.util import safe_tar, run_subprocess
from e4s_cl.logger import get_logger
from e4s_cl.util import which
from e4s_cl.cf.detect_name import _get_mpi_vendor_version, filter_mpi_libs

LOGGER = get_logger(__name__)

WI4MPI_RELEASE_URL = 'https://github.com/cea-hpc/wi4mpi/archive/refs/tags/v3.6.1.tar.gz'

WI4MPI_DIR = Path(E4S_CL_HOME) / "wi4mpi"

CPU_COUNT = os.cpu_count() or 2


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

    cmake_executable = which("cmake")
    if not cmake_executable:
        LOGGER.warning(
            "WI4MPI installation failed: cmake is missing. Proceeding with profile initialisation"
        )
        return False

    def _double_tap(cmd):
        """
        Run a given command (cmake/make) discarding the output. If the
        returncode indicates an error, run it again with the out/err streams
        enabled; this ensures a concise error output as recommended on the GNU
        make's website.
        """

        success = run_subprocess(cmd, discard_output=True)
        if success:
            LOGGER.debug(f"Command run failed: {cmd}, running with visible output.")
            run_subprocess(cmd, discard_output=False)

        return not success

    source_dir = download_wi4mpi(WI4MPI_RELEASE_URL, WI4MPI_DIR)
    build_dir = WI4MPI_DIR / 'build'
    install_dir = WI4MPI_DIR / 'install'

    if source_dir is None:
        LOGGER.error("Failed to access Wi4MPI release")
        return False

    configure_cmd = [
        cmake_executable, \
        f"-DCMAKE_INSTALL_PREFIX={install_dir}", \
        '-DWI4MPI_COMPILER=GNU', \
        source_dir.as_posix()
    ]

    build_cmd = [
        cmake_executable, \
        '--build', '.', \
        '--parallel', str(CPU_COUNT) \
    ]

    install_cmd = [
        cmake_executable, \
        '--build', '.', \
        '--target', 'install'
    ]

    try:
        if build_dir.exists():
            rmtree(build_dir)

        build_dir.mkdir(exist_ok=True)
        os.chdir(build_dir)
    except PermissionError as err:
        LOGGER.debug("Failed to create build directory %s: %s",
                     build_dir.as_posix(), str(err))
        return False
    LOGGER.warning(f"Attempting to install WI4MPI at {WI4MPI_DIR}")

    if _double_tap(configure_cmd) \
            and _double_tap(build_cmd) \
            and _double_tap(install_cmd):
        LOGGER.warning("WI4MPI is built and installed")
        return True

    LOGGER.warning("WI4MPI installation failed. Proceeding with profile initialisation")
    return False
