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
from elftools.elf.elffile import ELFFile

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


def _check_wi4mpi_install(install_dir: Path) -> bool:
    """
    Sanity check for the Wi4MPI installation
    """
    # Check binary existence
    binary = install_dir / 'bin' / 'wi4mpi'
    if not binary.exists():
        LOGGER.debug("Wi4MPI binary not found at %s", binary)
        return False

    # Check architecture of shares objects
    # Expected machine from os.uname().machine
    machine = os.uname().machine
    expected = {
        'x86_64': 'EM_X86_64',
        'amd64': 'EM_X86_64',
        'aarch64': 'EM_AARCH64',
        'ppc64le': 'EM_PPC64',
        'ppc64': 'EM_PPC64',
    }.get(machine)

    if expected:
        # Check libexec shared objects
        lib_dir = install_dir / 'libexec' / 'wi4mpi'
        libraries = list(lib_dir.glob('libwi4mpi_*.so'))

        if libraries:
            for lib in libraries:
                if not lib.is_file():
                    continue
                try:
                    with open(lib, 'rb') as f:
                        elf = ELFFile(f)
                        # Note: With pyelftools 0.27, header['e_machine'] returns a string like 'EM_X86_64'
                        # Both elf.header.e_machine and elf.header['e_machine'] work equivalently
                        machine_type = elf.header['e_machine']
                        if machine_type != expected:
                            LOGGER.error(
                                "Wi4MPI library %s architecture mismatch: expected %s, got %s",
                                lib.name, expected, machine_type)
                            return False
                except Exception as err:
                    LOGGER.debug("Failed to check architecture of %s: %s", lib,
                                 err)

    # Check if executable runs
    if run_subprocess([str(binary), '-h'], discard_output=True):
        LOGGER.error("Wi4MPI binary at %s failed to run", binary)
        return False

    return True


def install_wi4mpi(install_dir: Path) -> Optional[Path]:
    """Clones and installs wi4mpi from github releases"""

    if os.uname().machine not in {'x86_64', 'amd64', 'aarch64', 'ppc64le'}:
        LOGGER.warning(
            "Wi4MPI not available for the following architecture: %s",
            os.uname().machine)
        return None

    if install_dir.exists():
        if _check_wi4mpi_install(install_dir):
            LOGGER.debug(
                "Skipping installation for already installed Wi4MPI in %s",
                install_dir)
            return install_dir

        if list(install_dir.glob('*')):
            LOGGER.error(
                "Target directory %s is not empty and contains an invalid or incomplete Wi4MPI installation.",
                install_dir)
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

    # Apply custom CFLAGS/CXXFLAGS if provided via environment variables
    wi4mpi_cflags = os.environ.get('E4S_CL_WI4MPI_CFLAGS')
    wi4mpi_cxxflags = os.environ.get('E4S_CL_WI4MPI_CXXFLAGS')
    if wi4mpi_cflags:
        configure_cmd.append(f"-DCMAKE_C_FLAGS={wi4mpi_cflags}")
        LOGGER.debug("Using custom Wi4MPI CFLAGS: %s", wi4mpi_cflags)
    if wi4mpi_cxxflags:
        configure_cmd.append(f"-DCMAKE_CXX_FLAGS={wi4mpi_cxxflags}")
        LOGGER.debug("Using custom Wi4MPI CXXFLAGS: %s", wi4mpi_cxxflags)

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
