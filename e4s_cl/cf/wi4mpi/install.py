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

    cmake_executable = which("cmake")
    if not cmake_executable:
        LOGGER.warning(
            "WI4MPI installation failed: cmake is missing. Proceeding with profile initialisation"
        )
        return False

    def _run_wi4mpi_install_cmd(cmd, discard_output=True):
        """
        Run a command. Disables output on discard_output=True
        """
        # None is the default; no redirection
        stdout, stderr = None, None
        if discard_output:
            # Redirect output to null and error to output (to null)
            stdout, stderr = DEVNULL, STDOUT

        with subprocess.Popen(cmd, stdout=stdout, stderr=stderr) as proc:
            status = proc.wait()
        return status == 0

    def _double_tap(cmd):
        """
        Run a given command (cmake/make) discarding the output. If the
        returncode indicates an error, run it again with the out/err streams
        enabled; this ensures a concise error output as recommended on the GNU
        make's website.
        """

        success = _run_wi4mpi_install_cmd(cmd, discard_output=True)
        if not success:
            _run_wi4mpi_install_cmd(cmd, discard_output=False)

        return success

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
        '--parallel', \
    ]

    install_cmd = [
        cmake_executable, \
        '--build', '.', \
        '--target', 'install'
    ]

    try:
        build_dir.mkdir(exist_ok=True)
        os.chdir(build_dir)
    except PermissionError as err:
        LOGGER.debug("Failed to create directory %s: %s", build_dir.as_posix(),
                     str(err))
        return False

    if _double_tap(configure_cmd) \
            and _double_tap(build_cmd) \
            and _double_tap(install_cmd):
        LOGGER.warning(f"Wi4MPI is built and installed")
        return True

    return False
