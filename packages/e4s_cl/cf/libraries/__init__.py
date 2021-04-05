"""
Library analysis and manipulation helpers
"""

from e4s_cl.cf.version import Version
from e4s_cl.cf.libraries.ldcache import host_libraries
from e4s_cl.cf.libraries.ldd import ldd
from e4s_cl.cf.libraries.linker import resolve
from e4s_cl.cf.libraries.libraryset import LibrarySet, Library, HostLibrary, GuestLibrary

def extract_libc(text):
    """
    Extract libc version sumber from the output of ldd --version
    We could have used the libc but locating it would require some
    gymnastic, so accessing ldd seemed cleaner.
    EDIT - Almost deprecated, a switch in the scope of analysis made
    locating the libc cleaner. See the method below.
    """

    # The first line of output is usually:
    # > ldd (<noise with numbers>) x.y
    if not text:
        LOGGER.error("Failed to determine libc version from '%s'", text)
        return Version('0.0.0')

    try:
        version_string = text.split('\n')[0].split()[-1]
    except IndexError:
        LOGGER.error("Failed to determine libc version from '%s'", text)
        return Version('0.0.0')

    return Version(version_string)


HOST_LIBC = None


def libc_version():
    """
    Get the version number of the libc available on the host
    Caches the result
    """

    global HOST_LIBC

    if HOST_LIBC:
        return HOST_LIBC

    path = resolve('libc.so.6')

    if not path:
        raise InternalError("libc not found on host")

    with open(path, 'rb') as file:
        data = HostLibrary(file)

    # Get the version with major 2 from the defined versions,
    # as almost all libc implementations have the GLIBC_3.4 symbol
    HOST_LIBC = max(
        filter(lambda x: x and x.major == 2,
               [Version(s) for s in data.defined_versions]))

    return HOST_LIBC
