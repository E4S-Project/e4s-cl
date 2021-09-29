"""
Automatic name detector based on mpi vendor 
"""

import re
import ctypes
from pathlib import Path
from e4s_cl import logger, util
from e4s_cl.model.profile import Profile

LOGGER = logger.get_logger(__name__)

def _suffix_profile(profile_name: str) -> str:
    """
    Add a '-N' to a profile if it already exists
    """
    escaped_profile_name = re.escape(profile_name)
    pattern = re.compile("%s.*" % escaped_profile_name)
    matches = Profile.controller().match('name', regex=pattern)
    names = set(filter(None, map(lambda x: x.get('name'), matches)))

    # Do not append a suffix for the first unique profile
    if not profile_name in names:
        return profile_name

    # An exact match exists, filter the occurences of 'name-N' (clones)
    # and return name-max(N)+1
    clones = set(
        filter(
            None,
            map(lambda x: re.match("%s-(?P<ordinal>[0-9]*)" % escaped_profile_name, x),
                names)))

    # Try to list all clones of this profile
    ordinals = []
    for clone in clones:
        try:
            ordinals.append(int(clone.group('ordinal')))
        except ValueError:
            pass

    # If there are no clones, this is the second profile, after the original
    profile_no = 2
    if len(ordinals):
        profile_no = max(ordinals) + 1

    return '%s-%d' % (profile_name, profile_no)

def detect_name(path_list):
    """
    Given a list of shared objects, get an MPI library name and version
    """
    profile_name, version_str = '', ''
    version_buffer = ctypes.create_string_buffer(3000)
    length = ctypes.c_int()

    distro_dict = {
        'Intel(R) MPI':
        (lambda x: x.split("Library", 1)[1].split("for", 1)[0]),
        'Open MPI': (lambda x: x.split("v", 1)[1].split(",", 1)[0]),
        'Spectrum MPI': (lambda x: x.split("v", 1)[1].split(",", 1)[0]),
        'MPICH': (lambda x: x.split(":", 1)[1].split("M", 1)[0]),
        'MVAPICH': (lambda x: x.split(":", 1)[1].split("M", 1)[0])
    }

    def _extract_vinfo(path: Path):
        # Get the a handle to the MPI_Get_library_version function given
        # a path to a shared object
        if not path.exists():
            return None

        try:
            handle = ctypes.CDLL(path)
            return getattr(handle, 'MPI_Get_library_version', None)
        except OSError as err:
            LOGGER.debug("Error loading shared object %s: %s", path.as_posix(),
                         str(err))
            return None

    # Handles found in the library list
    version_f = list(filter(None, map(_extract_vinfo, path_list)))
    # Container for the results
    version_data = set()  # Set((Str, Version))

    for f in version_f:
        # Run every handle
        f(version_buffer, ctypes.byref(length))

        if length:
            version_buffer_str = version_buffer.value.decode("utf-8")[:500]

            # Check for keywords in the buffer
            filtered_buffer = set(
                filter(lambda x: x in version_buffer_str, distro_dict.keys()))

            if len(filtered_buffer) != 1:
                # If we found multiple vendors => error
                continue

            profile_name = filtered_buffer.pop()
            # Run the corresponding function on the buffer
            version_str = "_" + distro_dict.get(
                profile_name, lambda x: None)(version_buffer_str)

            # Add the result to the above container
            version_data.add((profile_name, version_str))

    found_vendors = set(map(lambda x: x[0], version_data))

    if len(found_vendors) == 1:
        # If one consistent vendor has been found
        profile_name, version_str = version_data.pop()
        profile_name = profile_name + version_str
        profile_name = ''.join(profile_name.split())

    return profile_name