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

# Symbols imported for ease of use
from e4s_cl.cf.libraries.ldd import ldd
from e4s_cl.cf.libraries.linker import resolve, host_libraries
from e4s_cl.cf.libraries.libraryset import LibrarySet, Library, HostLibrary, GuestLibrary

from elftools.elf.elffile import ELFFile

LOGGER = get_logger(__name__)


@lru_cache
def libc_version():
    """
    Get the version number of the libc available on the host
    Caches the result
    """
    if not (path := resolve('libc.so.6')):
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


def library_links(shared_object: Library):
    """
    This method resolves all the symbolic links that may exist and point to
    the argument.

    Given the directory:
    lrwxrwxrwx. 1 root root   16 May 13  2019 libmpi.so -> libmpi.so.12.1.1
    lrwxrwxrwx. 1 root root   16 May 13  2019 libmpi.so.12 -> libmpi.so.12.1.1
    -rwxr-xr-x. 1 root root 2.7M May 13  2019 libmpi.so.12.1.1

    If any of those 3 files were to be passed as an argument, all would be
    returned.
    """
    if not isinstance(shared_object, Library):
        raise InternalError("Wrong argument type for import_libraries: %s" %
                            type(shared_object))

    libname = Path(shared_object.binary_path).name

    # If no '.so' in the file name, bind anyway and exit
    if not match(r'.*\.so.*', libname):
        LOGGER.debug("library_links: Error in format of %s", libname)
        return {Path(shared_object.binary_path)}

    cleared = set()
    prefix = libname.split('.so')[0]
    library_file = realpath(shared_object.binary_path)

    def _glob_links(prefix_):
        for file in list(Path(library_file).parent.glob("%s.so*" % prefix_)):
            if realpath(file) == library_file:
                cleared.add(file)

    _glob_links(prefix)

    # glib files are named as libc-2.33.so, but the links are named libc.so.x
    if matches := match(r'(?P<prefix>lib[a-z]+)-2\.[0-9]+', prefix):
        _glob_links(matches.group('prefix'))

    return cleared
