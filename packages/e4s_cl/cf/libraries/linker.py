import os
from pathlib import Path
from e4s_cl.cf.libraries.ldcache import host_libraries

__LINKER_PATH = None


def __linker_path():
    """
    Return linker search paths, in order
    Sourced from `man ld.so`
    """
    global __LINKER_PATH

    if __LINKER_PATH is not None:
        return __LINKER_PATH

    default_path = ['/lib', '/usr/lib', '/lib64', '/usr/lib64']
    ld_library_path = os.environ.get('LD_LIBRARY_PATH', "").split(':')

    __LINKER_PATH = (ld_library_path, default_path)
    return __LINKER_PATH


def resolve(soname, rpath='', runpath=''):
    """
    Get a path towards a library from a given soname.
    Implements system rules and takes the environment into account
    """

    found = None

    def valid(path):
        return os.path.exists(path) and os.path.isdir(path)

    dynamic_paths = [rpath] + __linker_path()[0] + [runpath]
    default_paths = __linker_path()[1]

    for dir in filter(valid, dynamic_paths):
        potential_lib = Path(dir, soname).as_posix()
        if os.path.exists(potential_lib):
            found = potential_lib

    if not found and soname in host_libraries().keys():
        found = host_libraries()[soname]

    if not found:
        for dir in filter(valid, default_paths):
            potential_lib = Path(dir, soname).as_posix()
            if os.path.exists(potential_lib):
                found = potential_lib

    return os.path.realpath(found) if found else None
