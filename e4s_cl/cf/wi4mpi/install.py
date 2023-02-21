"""
Collection of functions to fetch and install Wi4MPI for a given mpi installation
"""

import os
from shutil import rmtree
import tarfile
import urllib.request
from pathlib import Path
from typing import Optional
from e4s_cl import (
    USER_PREFIX,
    WI4MPI_DIR,
)
from e4s_cl.util import (
    hash256,
    run_subprocess,
    safe_tar,
)
from e4s_cl.logger import get_logger
from e4s_cl.util import which
from e4s_cl.cf.version import Version
from e4s_cl.cf.wi4mpi import (WI4MPI_METADATA)
from e4s_cl.cf.compiler import (
    CompilerVendor,
    VENDOR_BINARIES,
    available_compilers,
)

LOGGER = get_logger(__name__)

WI4MPI_VERSION = Version('3.6.4')
WI4MPI_RELEASE_URL = f"https://github.com/cea-hpc/wi4mpi/archive/refs/tags/v{WI4MPI_VERSION}.tar.gz"
WI4MPI_RELEASE_SHA256 = "be1732a1aed1e2946873951a344b572f11f2a55cd06c634580a9398b5877e22a"
CPU_COUNT = os.cpu_count()

_WI4MPI_COMPILER_STRINGS = {
    CompilerVendor.GNU: 'GNU',
    CompilerVendor.INTEL: 'INTEL',
    CompilerVendor.LLVM: 'LLVM',
    CompilerVendor.PGI: 'PGI',
    CompilerVendor.ARMCLANG: 'ARMCLANG',
    CompilerVendor.FUJITSU: 'FUJITSU',
}


def _select_compiler() -> Optional[int]:
    """Returns the available compiler"""
    compilers = available_compilers()
    if not compilers:
        return None

    compiler = min(compilers)
    if compiler in _WI4MPI_COMPILER_STRINGS:
        return compiler
    return None


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

        with open(archive, 'rb') as data:
            checksum = hash256(data.read())
            if checksum != WI4MPI_RELEASE_SHA256:
                LOGGER.error(
                    "Downloaded file does not match checksum; aborting")
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

    LOGGER.debug("Double tapping: %s", " ".join(cmd))
    success = run_subprocess(cmd, discard_output=True)
    if success:
        LOGGER.debug("Command run failed: %s, running with visible output.",
                     cmd)
        run_subprocess(cmd, discard_output=False)

    return not success


def install_wi4mpi(install_dir: Path) -> Optional[Path]:
    """Clones and installs wi4mpi from github releases"""

    if os.uname().machine not in {'x86_64', 'amd64'}:
        LOGGER.warning(
            "Wi4MPI not available for the following architecture: %s",
            os.uname().machine)
        return None

    binary = install_dir / 'bin' / 'wi4mpi'
    if install_dir.exists() and binary.exists():
        LOGGER.debug(
            "Skipping installation for already installed Wi4MPI in %s",
            install_dir)
        return install_dir

    if install_dir.exists() and list(install_dir.glob('*')):
        LOGGER.error(
            "Attempting Wi4MPI installation in a non-empty directory: %s",
            str(install_dir))
        return None

    # Assert CMake is available
    cmake_executable = which("cmake")
    if not cmake_executable:
        LOGGER.error("Wi4MPI installation failed: cmake is missing.")
        return None

    compiler_id = _select_compiler()
    compiler = _WI4MPI_COMPILER_STRINGS.get(compiler_id)
    if compiler is None:
        LOGGER.error("No available compiler to build Wi4MPI: aborting.")
        return None

    source_dir = _download_wi4mpi(WI4MPI_DIR)
    if source_dir is None:
        LOGGER.error("Failed to download Wi4MPI release; aborting")
        return None

    build_dir = WI4MPI_DIR / 'build'
    c_compiler, cxx_compiler, fortran_compiler = VENDOR_BINARIES.get(
        compiler_id)

    configure_cmd = [
        cmake_executable,
        "-B",
        str(build_dir),
        "-S",
        str(source_dir),
        f"-DCMAKE_INSTALL_PREFIX={install_dir}",
        f"-DCMAKE_C_COMPILER={c_compiler}",
        f"-DCMAKE_CXX_COMPILER={cxx_compiler}",
        f"-DCMAKE_FC_COMPILER={fortran_compiler}",
        f"-DWI4MPI_COMPILER={compiler}",
        source_dir.as_posix(),
    ]

    build_cmd = [
        cmake_executable,
        "--build",
        str(build_dir),
        '--parallel',
        str(CPU_COUNT),
    ]

    install_cmd = [
        cmake_executable,
        '--build',
        str(build_dir),
        '--target',
        'install',
    ]

    try:
        if build_dir.exists():
            rmtree(build_dir)

        build_dir.mkdir(exist_ok=True)
    except PermissionError as err:
        LOGGER.debug("Failed to create build directory %s: %s",
                     build_dir.as_posix(), str(err))
        return None

    LOGGER.info("Installing Wi4MPI in %s", install_dir)

    if _double_tap(configure_cmd) \
            and _double_tap(build_cmd) \
            and _double_tap(install_cmd):
        LOGGER.info("Wi4MPI has been built and installed")
        return install_dir

    LOGGER.error("Wi4MPI installation failed: MPI translation may fail.")
    rmtree(install_dir, ignore_errors=True)
    return None
