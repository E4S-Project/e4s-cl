"""
Collection of functions to fetch and install Wi4MPI for a given mpi installation
"""

import os
from shutil import rmtree
import tarfile
import urllib.request
from pathlib import Path
from typing import Optional
from e4s_cl import USER_PREFIX
from e4s_cl.util import safe_tar, run_subprocess
from e4s_cl.logger import get_logger
from e4s_cl.util import which
from e4s_cl.cf.version import Version
from e4s_cl.cf.wi4mpi import (WI4MPI_METADATA)
from e4s_cl.cf.detect_mpi import MPIIdentifier
from e4s_cl.cf.compiler import CompilerVendor, available_compilers

LOGGER = get_logger(__name__)

WI4MPI_VERSION = Version('3.6.2')
WI4MPI_RELEASE_URL = f"https://github.com/cea-hpc/wi4mpi/archive/refs/tags/v{WI4MPI_VERSION}.tar.gz"
WI4MPI_DIR = Path(USER_PREFIX) / "wi4mpi"

CPU_COUNT = os.cpu_count()

# List of MPI distributions requiring Wi4MPI for proper e4s-cl support
# The keys correspond to possible values of MPIIdentifier.vendor
_WI4MPI_DEPENDENT = {
    'Open MPI': True,
}

_WI4MPI_COMPILER_STRINGS = {
    CompilerVendor.GNU: 'GNU',
    CompilerVendor.INTEL: 'INTEL',
    CompilerVendor.LLVM: 'LLVM',
    CompilerVendor.PGI: 'PGI',
    CompilerVendor.ARMCLANG: 'ARMCLANG',
    CompilerVendor.FUJITSU: 'FUJITSU',
}


def _select_compiler() -> Optional[str]:
    """Returns the expected string for the available compiler"""
    compilers = available_compilers()

    if not compilers:
        return None

    return _WI4MPI_COMPILER_STRINGS.get(min(compilers))


def requires_wi4mpi(mpi_id: MPIIdentifier) -> bool:
    """
    Checks if the mpi vendor detected needs wi4mpi in order to function
    correctly with e4s-cl, and if so installs it.
    """
    if not isinstance(mpi_id, MPIIdentifier):
        return False
    return mpi_id.vendor in _WI4MPI_DEPENDENT


def _fetch_release(destination: Path) -> Optional[Path]:
    """Fetch an url and write it to a temporary file"""
    archive_file = destination / f"wi4mpi-{WI4MPI_VERSION}.tgz"

    if not archive_file.exists():
        try:
            with urllib.request.urlopen(WI4MPI_RELEASE_URL) as request:
                if not request.status == 200:
                    return None

                with open(archive_file, mode='w+b') as buffer:
                    buffer.write(request.read())
        except (ValueError, urllib.error.URLError) as err:
            LOGGER.error("Error fetching URL: %s", err)
            return None

    return archive_file


def _download_wi4mpi(destination: Path) -> Optional[Path]:
    """
    Download and extract the TAR archive from 'url' into the directory 'destination'
    """
    if not destination.exists():
        destination.mkdir()

    try:
        archive = _fetch_release(destination)
        if archive is None or not tarfile.is_tarfile(archive):
            LOGGER.error("Downloaded file is not an archive; aborting")
            return None

        with tarfile.open(archive) as data:
            if not safe_tar(data):
                LOGGER.error("Unsafe paths detected in archive; aborting")
                return None

            release_root_dir = min(data.getnames())

            if not (destination / release_root_dir).exists():
                data.extractall(destination)
    except PermissionError as err:
        LOGGER.error("Failed to download Wi4MPI sources: %s", err)
        return None

    return destination / release_root_dir


def _update_config(config_path: Path, key: str, value: str) -> None:
    """Modify the configuration at a given path for key to hold value"""
    with open(config_path, mode='r', encoding='utf-8') as config_file:
        config = config_file.readlines()

    done = False
    directive = f"{key}=\"{value}\"\n"

    for index, line in enumerate(config):
        if not done and line.startswith(key):
            config[index] = directive
            done = True

    if not done:
        config.append(directive)

    with open(config_path, mode='w', encoding='utf-8') as config_file:
        config_file.writelines(config)


def overwrite_config(config_path: Path, key: str, value: str) -> None:
    """Make sure the only defined key in the configuration is the one passed as
    an argument"""
    for vendor in WI4MPI_METADATA:
        _update_config(config_path, vendor.default_path_key, '')
    _update_config(config_path, key, value)


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


def install_wi4mpi(install_dir: Path) -> Optional[Path]:
    """Clones and installs wi4mpi from git run
    
    Installs in ~/.local/share/wi4mpi using a GNU compiler
    """

    # Assert CMake is available
    cmake_executable = which("cmake")
    if not cmake_executable:
        LOGGER.warning(
            "Wi4MPI installation failed: cmake is missing. Proceeding with profile initialisation"
        )
        return None

    compiler = _select_compiler()
    if compiler is None:
        LOGGER.error("No available compiler to build Wi4MPI: aborting.")
        return None

    source_dir = _download_wi4mpi(WI4MPI_DIR)
    if source_dir is None:
        LOGGER.error("Failed to download Wi4MPI release; aborting")
        return None

    build_dir = WI4MPI_DIR / 'build'

    configure_cmd = [
        cmake_executable, \
        f"-DCMAKE_INSTALL_PREFIX={install_dir}", \
        f"-DWI4MPI_COMPILER={compiler}", \
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

    if install_dir.exists():
        LOGGER.debug(
            "Skipping installation for already installed Wi4MPI in %s",
            install_dir)
        return install_dir

    try:
        if build_dir.exists():
            rmtree(build_dir)

        build_dir.mkdir(exist_ok=True)
        os.chdir(build_dir)
    except PermissionError as err:
        LOGGER.debug("Failed to create build directory %s: %s",
                     build_dir.as_posix(), str(err))
        return None

    LOGGER.warning("Installing Wi4MPI in %s", install_dir)

    if _double_tap(configure_cmd) \
            and _double_tap(build_cmd) \
            and _double_tap(install_cmd):
        LOGGER.warning("Wi4MPI has been built and installed")
        return install_dir

    LOGGER.warning(
        "Wi4MPI installation failed. Proceeding with profile initialisation")
    rmtree(install_dir, ignore_errors=True)
    return None
