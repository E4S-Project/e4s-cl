"""
Library analysis and manipulation helpers
"""

from re import match
from os.path import realpath
from pathlib import Path
from functools import lru_cache
from e4s_cl.error import InternalError
from e4s_cl.logger import get_logger
from e4s_cl.cf.version import Version
from e4s_cl.util import JSON_HOOKS

# Symbols imported for ease of use
from sotools import is_elf, library_links
from sotools.ldd import ldd
from sotools.linker import resolve, host_libraries
from sotools.libraryset import LibrarySet, Library

LOGGER = get_logger(__name__)


@lru_cache()
def libc_version():
    """
    -> e4s_cl.cf.version.Version
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


# pylint: disable=too-few-public-methods
class HostLibrary(Library):
    pass


# pylint: disable=too-few-public-methods
class GuestLibrary(Library):
    pass


def __library_decoder(_type):

    def __l_decoder(obj):
        out = _type()

        for key, value in obj.items():
            setattr(out, key, value)

        return out

    return __l_decoder


JSON_HOOKS['Library'] = __library_decoder(Library)
JSON_HOOKS['HostLibrary'] = __library_decoder(HostLibrary)
JSON_HOOKS['GuestLibrary'] = __library_decoder(GuestLibrary)
