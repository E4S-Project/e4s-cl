"""
Automatic name detector based on mpi vendor 
"""

import re
import ctypes
from pathlib import Path
from e4s_cl import logger
from e4s_cl.model.profile import Profile
from e4s_cl.cf.libraries import LibrarySet

LOGGER = logger.get_logger(__name__)


def _suffix_name(name: str, existing_names: set) -> str:
    """
    Add a '-N' to a profile if it already exists
    """
    # Do not append a suffix for the first unique profile
    if not name in existing_names:
        return name

    # An exact match exists, filter the occurences of 'name-N' (clones)
    # and return name-max(N)+1
    clones = set(
        filter(
            None,
            map(
                lambda x: re.match(f"{re.escape(name)}-(?P<ordinal>[0-9]*)", x
                                   ), existing_names)))

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


distro_dict = {
    'Intel(R) MPI': _extract_intel_mpi_version,
    'Open MPI': _extract_open_mpi_version,
    'Spectrum MPI': _extract_spectrum_mpi_version,
    'MPICH': _extract_mpich_version,
    'CRAY MPICH': _extract_cray_mpich_version,
    'MVAPICH': _extract_mvapich_version
}


def _extract_vinfo(path: Path):
    """
    Get the a handle to the MPI_Get_library_version function given
    a path to a shared object
    """
    if not path.exists():
        return None

    try:
        handle = ctypes.CDLL(path)
        return getattr(handle, 'MPI_Get_library_version', None)
    except OSError as err:
        LOGGER.debug("Error loading shared object %s: %s", path.as_posix(),
                     str(err))
        return None


def version_info(shared_object: Path):
    """
    Return the output of the MPI_Get_library_version in the shared object passed as an argument
    """

    if isinstance(shared_object, str):
        shared_object = Path(shared_object)

    # C-compatible buffer to run a C handle with
    version_buffer = ctypes.create_string_buffer(3000)
    length = ctypes.c_int()

    handle = _extract_vinfo(shared_object)
    if not handle:
        LOGGER.debug("Extracting MPI_Get_library_version from %s failed",
                     shared_object.as_posix())
        return None

    handle(version_buffer, ctypes.byref(length))

    if length:
        return version_buffer.value.decode("utf-8")[:500]
    return None


def detect_name(path_list):
    """
    Given a list of shared objects, get an MPI library name and version
    """
    profile_name, version_str = '', ''

    def _check_spectrum(vendors_list):
        return set(['Spectrum MPI', 'Open MPI']).issubset(set(vendors_list))

    # Container for the results
    version_data = set()  # set((str, str))

    for path in path_list:
        version_buffer_str = version_info(path)

        if version_buffer_str:
            # Check for keywords in the buffer
            filtered_buffer = set(
                filter(lambda x, buf=version_buffer_str: x in buf,
                       distro_dict.keys()))

            if len(filtered_buffer) != 1:
                if _check_spectrum(filtered_buffer):
                    filtered_buffer = ['Spectrum MPI']
                else:
                    # If we found multiple vendors, without it being Spectrum MPI and OpenMPI => error
                    continue

            profile_name = filtered_buffer.pop()
            # Run the corresponding function on the buffer
            # In case of an error, skip this function
            try:
                version_str = "_" + distro_dict.get(
                    profile_name, lambda x: None)(version_buffer_str)
            except:
                continue

            # Add the result to the above container
            version_data.add((profile_name, version_str))

    found_vendors = set(map(lambda x: x[0], version_data))
    if len(found_vendors) == 1:
        # If one consistent vendor has been found
        profile_name, version_str = version_data.pop()
        profile_name = profile_name + version_str
        profile_name = ''.join(profile_name.split())

    return profile_name


def try_rename(profile_id: str) -> None:
    """
    Analyze the selected profile for MPI libraries and rename it according
    to the vendor/version info in the shared object
    """
    data = Profile.controller().one({'name': profile_id})
    if not data:
        LOGGER.debug("Error renaming profile: profile '%s' not found",
                     profile_id)
        return

    # Extract all libmpi* libraries from the profile
    detected_libs = LibrarySet.create_from(data.get('libraries', []))
    mpi_libs = list(
        filter(lambda x: re.match(r'libmpi.*so.*', x.soname), detected_libs))

    # Run the methods in the libraries to get a version
    new_name = detect_name([Path(x.binary_path) for x in mpi_libs])

    if not new_name:
        LOGGER.debug("Profile naming failed")
        return

    LOGGER.debug("Found library %s", new_name)

    # Get all profiles matching the new name
    matches = Profile.controller().match('name',
                                         regex=f"{re.escape(new_name)}.*")
    names = set(filter(None, map(lambda x: x.get('name'), matches)))

    # Add a suffix to the name to avoid conflict
    profile_name = _suffix_name(new_name, names)

    # Update the profile name
    Profile.controller().update({'name': profile_name}, Profile.selected().eid)
