"""
Identify a MPI vendor and version from an ELF binary
"""

import re
import ctypes
from typing import Optional, Callable, Iterable, List, Set
from dataclasses import dataclass
from pathlib import Path
from e4s_cl import logger
from e4s_cl.model.profile import Profile

LOGGER = logger.get_logger(__name__)


@dataclass(frozen=True)
class MPIIdentifier:
    vendor: str
    version: str

    def __str__(self):
        return f"{self.vendor}@{self.version}".replace(' ', '_')


def _suffix_name(name: str, existing_names: set) -> str:
    """Compute a '-N' suffix for new profiles"""
    # Do not append a suffix for the first unique profile
    if name not in existing_names:
        return name

    # An exact match exists, filter the occurrences of 'name-N' (clones)
    # and return name-max(N)+1
    clones = set(
        filter(
            None,
            map(lambda x: re.match(fr"{re.escape(name)}-(?P<ordinal>\d*)", x),
                existing_names)))

    # Try to list all clones of this profile
    ordinals = []
    for clone in clones:
        try:
            ordinals.append(int(clone.group('ordinal')))
        except ValueError:
            pass

    # If there are no clones, this is the second profile, after the original
    ordinal = 2
    if len(ordinals) != 0:
        ordinal = max(ordinals) + 1

    return f"{name}-{ordinal}"


def strip(function):
    """Strip the output of the given function and catch IndexErrors"""

    def wrapper(version_buffer_str):
        version_str = ''

        try:
            version_str = function(version_buffer_str).strip()
        except IndexError:
            pass

        return version_str

    return wrapper


@strip
def _extract_intel_mpi_version(version_buffer_str: str) -> str:
    """
    Parses the typical Intel MPI library version message, eg:
    Intel(R) MPI Library 2019 Update 6 for Linux* OS
    """
    return version_buffer_str.split("Library", 1)[1].split("for", 1)[0]


@strip
def _extract_open_mpi_version(version_buffer_str: str) -> str:
    """
    Parses the typical OpenMPI library version message, eg:
    Open MPI v4.0.1, package: Open MPI Distribution, ident: 4.0.1, repo rev: v4.0.1, Mar 26, 2019
    """
    return version_buffer_str.split("v", 1)[1].split(",", 1)[0]


@strip
def _extract_spectrum_mpi_version(version_buffer_str: str) -> str:
    """
    Parses the typical Spectrum MPI library version message, eg:
    Open MPI v4.0.1, package: Spectrum MPI Distribution, ident: 4.0.1, repo rev: v4.0.1, Mar 26, 2019
    """
    return version_buffer_str.split("v", 1)[1].split(",", 1)[0]


@strip
def _extract_mpich_version(version_buffer_str: str) -> str:
    """
    Parses the typical MPICH library version message, eg:
    MPICH Version:  3.3b2
    MPICH Release date: Mon Apr  9 17:58:42 CDT 2018
    [...]
    """
    return version_buffer_str.split(":", 1)[1].split("M", 1)[0]


@strip
def _extract_cray_mpich_version(version_buffer_str: str) -> str:
    """
    Parses the typical MPICH library version message, eg:
    MPICH Version:  3.3b2
    MPICH Release date: Mon Apr  9 17:58:42 CDT 2018
    [...]
    """
    return version_buffer_str.split("version", 1)[1].split("(", 1)[0]


@strip
def _extract_mvapich_version(version_buffer_str: str) -> str:
    """
    Parses the typical MVAPICH library version message, eg:
    MVAPICH Version:  3.3b2
    MVAPICH Release date: Mon Apr  9 17:58:42 CDT 2018
    [...]
    """
    return version_buffer_str.split(":", 1)[1].split("M", 1)[0]


VENDOR_VERSION_EXTRACTORS = {
    'Intel(R) MPI': _extract_intel_mpi_version,
    'Open MPI': _extract_open_mpi_version,
    'Spectrum MPI': _extract_spectrum_mpi_version,
    'CRAY MPICH': _extract_cray_mpich_version,
    'MPICH': _extract_mpich_version,
    'MVAPICH': _extract_mvapich_version
}


def _get_mpi_handle(path: Path) -> Optional[Callable]:
    """Get a handle to the MPI_Get_library_version symbol given a path to a
    shared object"""
    if not path.exists():
        return None

    try:
        handle = ctypes.CDLL(path.as_posix())
        return getattr(handle, 'MPI_Get_library_version', None)
    except OSError as err:
        LOGGER.debug("Error loading shared object %s: %s", path.as_posix(),
                     str(err))
        return None


def _get_mpi_library_version(path: Path) -> str:
    """Return the output of the MPI_Get_library_version symbol in the MPI
    binary passed as an argument"""

    if isinstance(path, str):
        path = Path(path)

    # C-compatible buffer to run a C handle with
    version_buffer = ctypes.create_string_buffer(3000)
    length = ctypes.c_int()

    # Get a callable towards the C code
    handle = _get_mpi_handle(path)
    if not handle:
        LOGGER.debug("Extracting MPI_Get_library_version from %s failed",
                     path.as_posix())
        return ''

    # Execute the C code to fill the above buffer
    handle(version_buffer, ctypes.byref(length))

    if length:
        return version_buffer.value.decode("utf-8")[:500]
    return ''


def _get_mpi_vendor_version(path: Path) -> Optional[MPIIdentifier]:
    """Return a tuple of string according to the vendor and version of the MPI
    binary passed as an argument"""
    raw_str = _get_mpi_library_version(path)

    # Check for vendor keywords in the buffer
    filtered_buffer = list(
        filter(lambda x: x in raw_str, VENDOR_VERSION_EXTRACTORS.keys()))

    # Skip this binary if none were found
    if not filtered_buffer:
        return None

    # Sort vendors by size, and save the longest match
    filtered_buffer.sort(key=len, reverse=True)
    vendor_name = filtered_buffer[0]

    # Run the corresponding function on the buffer
    # In case of an error, skip this function
    try:
        version_str = VENDOR_VERSION_EXTRACTORS.get(
            vendor_name, lambda x: 'UNKNOWN_VERSION')(raw_str)
    except IndexError:
        return None

    return MPIIdentifier(vendor_name, version_str)


def detect_mpi(path_list: Iterable[Path]) -> Optional[MPIIdentifier]:
    """Parse the binaries from paths passed as arguments to get a `VENDOR@VERSION` string"""
    # Set of all MPI vendors and versions found in the binaries
    version_data = set(filter(None, map(_get_mpi_vendor_version, path_list)))

    # If one consistent vendor has been found
    if len(version_data) == 1:
        return version_data.pop()
    return None


def filter_mpi_libs(libraries: List[Path]) -> Set[Path]:
    """Return a set of MPI libraries from a list of libraries"""

    def _filter_mpi(path: Path):
        return re.match(r'libmpi.*so.*', path.name)

    return set(filter(_filter_mpi, libraries))


def install_dir(libraries: Iterable[Path]) -> Optional[Path]:
    """
    Return the installation directory of a given list of libraries, defined as
    the common path stub containing the 'lib' folder
    """

    def _stub(library: Path) -> Optional[Path]:
        try:
            lib_index = library.parts.index('lib')
        except ValueError:
            return None
        return Path(*library.parts[:lib_index])

    # Get a set of all the returns of _stub, filtering out the null values
    potential_installs = set(filter(None, map(_stub, libraries)))

    if len(potential_installs) == 1:
        return potential_installs.pop()
    return None


def profile_mpi_name(mpi_libs: Iterable[Path]) -> Optional[str]:
    """
    Analyze the profile with the given eid for MPI libraries and rename it
    according to the vendor/version info in the shared object
    """
    controller = Profile.controller()

    # Run the methods in the libraries to get a version
    mpi_id = detect_mpi(mpi_libs)

    if not mpi_id:
        LOGGER.debug("No symbol found in %s", " ".join(map(str, mpi_libs)))
        return None

    LOGGER.debug("Found identifier %s from profile's MPI libraries", mpi_id)

    # Get all profiles matching the new name
    matches = controller.match('name', regex=f"{re.escape(str(mpi_id))}.*")
    matching_names = set(filter(None, map(lambda x: x.get('name'), matches)))

    # Add a suffix to the name to avoid conflict
    return _suffix_name(str(mpi_id), matching_names)
