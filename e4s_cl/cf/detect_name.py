"""
Automatic name detector based on mpi vendor 
"""

import re
import ctypes
from typing import Optional, Callable, Iterable, Tuple
from pathlib import Path
from e4s_cl import logger
from e4s_cl.error import UniqueAttributeError
from e4s_cl.model.profile import Profile
from e4s_cl.util import install_wi4mpi

LOGGER = logger.get_logger(__name__)


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

    def wrapper(version_buffer_str):
        return function(version_buffer_str).strip()

    return wrapper


@strip
def _extract_intel_mpi_version(version_buffer_str):
    """
    Parses the typical Intel MPI library version message, eg:
    Intel(R) MPI Library 2019 Update 6 for Linux* OS
    """
    return version_buffer_str.split("Library", 1)[1].split("for", 1)[0]


@strip
def _extract_open_mpi_version(version_buffer_str):
    """
    Parses the typical OpenMPI library version message, eg:
    Open MPI v4.0.1, package: Open MPI Distribution, ident: 4.0.1, repo rev: v4.0.1, Mar 26, 2019
    """
    return version_buffer_str.split("v", 1)[1].split(",", 1)[0]


@strip
def _extract_spectrum_mpi_version(version_buffer_str):
    """
    Parses the typical Spectrum MPI library version message, eg:
    Open MPI v4.0.1, package: Spectrum MPI Distribution, ident: 4.0.1, repo rev: v4.0.1, Mar 26, 2019
    """
    return version_buffer_str.split("v", 1)[1].split(",", 1)[0]


@strip
def _extract_mpich_version(version_buffer_str):
    """
    Parses the typical MPICH library version message, eg:
    MPICH Version:  3.3b2
    MPICH Release date: Mon Apr  9 17:58:42 CDT 2018
    [...]
    """
    return version_buffer_str.split(":", 1)[1].split("M", 1)[0]


@strip
def _extract_cray_mpich_version(version_buffer_str):
    """
    Parses the typical MPICH library version message, eg:
    MPICH Version:  3.3b2
    MPICH Release date: Mon Apr  9 17:58:42 CDT 2018
    [...]
    """
    return version_buffer_str.split("version", 1)[1].split("(", 1)[0]


@strip
def _extract_mvapich_version(version_buffer_str):
    """
    Parses the typical MVAPICH library version message, eg:
    MVAPICH Version:  3.3b2
    MVAPICH Release date: Mon Apr  9 17:58:42 CDT 2018
    [...]
    """
    return version_buffer_str.split(":", 1)[1].split("M", 1)[0]

def _install_wi4mpi():
    install_wi4mpi()

def nop():
    pass

distro_dict = {
    'Intel(R) MPI': (_extract_intel_mpi_version, nop),
    'Open MPI': (_extract_open_mpi_version, _install_wi4mpi),
    'Spectrum MPI': (_extract_spectrum_mpi_version, nop),
    'CRAY MPICH': (_extract_cray_mpich_version, nop),
    'MPICH': (_extract_mpich_version, nop),
    'MVAPICH': (_extract_mvapich_version, nop)
}


def _get_mpi_handle(path: Path) -> Optional[Callable]:
    """Get a handle to the MPI_Get_library_version symbol given a path to a shared object"""
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
    """Return the output of the MPI_Get_library_version symbol in the MPI binary passed as an argument"""

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


def _get_mpi_vendor_version(path: Path) -> Optional[Tuple[str, str]]:
    """Return a tuple of string according to the vendor and version of the MPI
    binary passed as an argument"""
    raw_str = _get_mpi_library_version(path)

    # Check for vendor keywords in the buffer
    filtered_buffer = list(filter(lambda x: x in raw_str, distro_dict.keys()))

    # Skip this binary if none were found
    if not filtered_buffer:
        return None

    # Sort vendors by size, and save the longest match
    filtered_buffer.sort(key=len, reverse=True)
    vendor_name = filtered_buffer[0]

    # Run the corresponding function on the buffer
    # In case of an error, skip this function
    try:
        version_str = distro_dict.get(vendor_name,
                                      lambda x: 'UNKNOWN_VERSION')[0](raw_str)
    except IndexError:
        return None

    return vendor_name, version_str

def detect_mpi(path_list: Iterable[Path]) -> str:
    """Parse the binaries from paths passed as arguments to get a `VENDOR@VERSION` string"""
    profile_name = ''

    # Set of all MPI vendors and versions found in the binaries
    version_data = set(filter(None, map(_get_mpi_vendor_version, path_list)))

    # Set of all unique vendors
    found_vendors = set(map(lambda x: x[0], version_data))

    # If one consistent vendor has been found
    if len(found_vendors) == 1:
        profile_name = "@".join(version_data.pop()).replace(' ', '_')

    return profile_name

def filter_mpi_libs(data):

    def _filter_mpi(path: Path):
        return re.match(r'libmpi.*so.*', path.name)

    detected_libs = set(map(Path, data.get('libraries', [])))
    mpi_libs = set(filter(_filter_mpi, detected_libs))

    return mpi_libs

def check_wi4mpi(profile):
    mpi_libs = filter_mpi_libs(profile)
    vendor_list = list(filter(None, map(_get_mpi_vendor_version, mpi_libs)))
    if vendor_list:
        vendor = vendor_list[0][0]
        distro_dict.get(vendor)[1]()

def rename_profile_mpi_version(profile_eid: int) -> bool:
    """
    Analyze the profile with the given eid for MPI libraries and rename it
    according to the vendor/version info in the shared object
    """
    controller = Profile.controller()
    data = controller.one(profile_eid)
    if not data:
        LOGGER.debug("Error renaming profile: profile id '%d' not found",
                     profile_eid)
        return False

    # Extract all libmpi* libraries from the profile
    mpi_libs = filter_mpi_libs(data)
    
    # Run the methods in the libraries to get a version
    mpi_id = detect_mpi(mpi_libs)

    if not mpi_id:
        LOGGER.debug("Profile naming failed: no symbol found in %s",
                     " ".join(map(str, mpi_libs)))
        return False

    LOGGER.debug("Found identifier %s from profile's MPI libraries", mpi_id)

    # Get all profiles matching the new name
    matches = Profile.controller().match('name',
                                         regex=f"{re.escape(mpi_id)}.*")
    matching_names = set(filter(None, map(lambda x: x.get('name'), matches)))

    # Add a suffix to the name to avoid conflict
    profile_name = _suffix_name(mpi_id, matching_names)

    # Update the profile name
    try:
        controller.update({'name': profile_name}, profile_eid)
    except UniqueAttributeError:
        LOGGER.error(
            "Error updating profile '%s' name to '%s': another profile exists",
            data['name'], profile_name)
        return False

    return True
