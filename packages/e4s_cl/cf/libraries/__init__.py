"""
Library analysis and manipulation helpers
"""

from functools import lru_cache
from e4s_cl.error import InternalError
from e4s_cl.cf.version import Version

# Symbols imported for ease of use
from e4s_cl.cf.libraries.ldcache import host_libraries
from e4s_cl.cf.libraries.ldd import ldd
from e4s_cl.cf.libraries.linker import resolve
from e4s_cl.cf.libraries.libraryset import LibrarySet, Library, HostLibrary, GuestLibrary

from elftools.elf.elffile import ELFFile


@lru_cache
def libc_version():
    """
    Get the version number of the libc available on the host
    Caches the result
    """
    path = resolve('libc.so.6')

    if not path:
        raise InternalError("libc not found on host")

    with open(path, 'rb') as file:
        data = HostLibrary(file)

    # Get the version with major 2 from the defined versions,
    # as almost all libc implementations have the GLIBC_3.4 symbol
    libc_ver = max(
        filter(lambda x: x and x.major == 2,
               [Version(s) for s in data.defined_versions]))

    return libc_ver


def is_elf(path):
    """
    It's dirty, but that is the best I could find in the elftools module
    """
    try:
        with open(path, 'rb') as target:
            ELFFile(target)
    except:
        return False

    return True
