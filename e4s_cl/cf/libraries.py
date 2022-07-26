"""
Library analysis and manipulation helpers
"""

from functools import lru_cache

# Symbols imported for ease of use
# pylint: disable=W0611
from sotools import is_elf, library_links
# pylint: disable=W0611
from sotools.ldd import ldd
# pylint: disable=W0611
from sotools.linker import resolve
# pylint: disable=W0611
from sotools.libraryset import LibrarySet, Library
# pylint: disable=W0611
from sotools.dl_cache import cache_libraries

from e4s_cl.error import InternalError
from e4s_cl.logger import get_logger
from e4s_cl.cf.version import Version
from e4s_cl.util import JSON_HOOKS

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

    data = Library.from_path(path)

    # Get the version with major 2 from the defined versions,
    # as almost all libc implementations have the GLIBC_3.4 symbol
    libc_ver = max(
        filter(lambda x: x and x.major == 2,
               [Version(s) for s in data.defined_versions]))

    return libc_ver
