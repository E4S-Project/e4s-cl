"""
Collection of functions to fetch and install Wi4MPI for a given mpi installation
"""

import os
from shutil import rmtree
import tarfile
import urllib.request
from pathlib import Path
from typing import Optional, List
from tempfile import NamedTemporaryFile
from e4s_cl import E4S_CL_HOME
from e4s_cl.util import safe_tar, run_subprocess
from e4s_cl.logger import get_logger
from e4s_cl.util import which
from e4s_cl.cf.detect_mpi import detect_mpi

LOGGER = get_logger(__name__)

WI4MPI_RELEASE_URL = 'https://github.com/cea-hpc/wi4mpi/archive/refs/tags/v3.6.1.tar.gz'
WI4MPI_DIR = Path(E4S_CL_HOME) / "wi4mpi"

CPU_COUNT = os.cpu_count() or 2

DISTRO_DICT = {
    'Intel(R) MPI': False,
    'Open MPI': True,
    'Spectrum MPI': False,
    'CRAY MPICH': False,
    'MPICH': False,
    'MVAPICH': False
}

VENDOR_DICT = {
    'Intel(R) MPI': 'intelmpi',
    'Open MPI': 'openmpi',
    'MPICH': 'mpich',
}

CONFIG_KEY_DICT = {
    'Intel(R) MPI': 'INTELMPI_DEFAULT_ROOT',
    'Open MPI': 'OPENMPI_DEFAULT_ROOT',
    'MPICH': 'MPICH_DEFAULT_ROOT',
}


def requires_wi4mpi(libraries: List) -> bool:
    """
    Checks if the mpi vendor detected needs wi4mpi in order to function
    correctly with e4s-cl, and if so installs it.
    """
    mpi_id = detect_mpi(libraries)
    if mpi_id:
        return DISTRO_DICT.get(mpi_id.vendor, False), mpi_id
    return False, ''


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


def update_config(config_path: Path, key: str, value: str) -> None:
    """Modify the configuration at a given path for key to hold value"""
    with open(config_path, mode='r', encoding='utf-8') as config_file:
        config = config_file.readlines()

    done = False
    line = f"{key}=\"{value}\"\n"

    for index, line in enumerate(config):
        if not done and line.startswith(key):
            config[index] = line
            done = True

    if not done:
        config.append(line)

    with open(config_path, mode='w', encoding='utf-8') as config_file:
        config_file.writelines(config)


def _double_tap(cmd):
    """
    Run a given command (cmake/make) discarding the output. If the
    returncode indicates an error, run it again with the out/err streams
    enabled; this ensures a concise error output as recommended on the GNU
    make's website.
    """

    success = run_subprocess(cmd, discard_output=True)
    if success:
        LOGGER.debug("Command run failed: %s, running with visible output.",
                     cmd)
        run_subprocess(cmd, discard_output=False)

    return not success


def install_wi4mpi(mpi_id, mpi_install_dir) -> bool:
    """Clones and installs wi4mpi from git run
    
    Installs in ~/.local/share/wi4mpi using a GNU compiler
    """

    # Needed to update the configuration file
    if mpi_id.vendor not in CONFIG_KEY_DICT:
        LOGGER.error('Unrecognized MPI distribution: %s', mpi_id.vendor)
        return False

    # Assert CMake is available
    cmake_executable = which("cmake")
    if not cmake_executable:
        LOGGER.warning(
            "WI4MPI installation failed: cmake is missing. Proceeding with profile initialisation"
        )
        return False

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
    LOGGER.warning("Installing WI4MPI in %s", WI4MPI_DIR)

    if _double_tap(configure_cmd) \
            and _double_tap(build_cmd) \
            and _double_tap(install_cmd):
        update_config(install_dir / 'etc' / 'wi4mpi.cfg',
                      CONFIG_KEY_DICT.get(mpi_id.vendor), mpi_install_dir)
        LOGGER.warning("WI4MPI has been built and installed")
        return True

    LOGGER.warning(
        "WI4MPI installation failed. Proceeding with profile initialisation")
    return False
