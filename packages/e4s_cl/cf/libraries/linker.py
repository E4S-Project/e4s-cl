"""
Implementation of the dynamic linker search algorithm
Rules in ld.so(8)
"""

import os
import re
from tempfile import NamedTemporaryFile
from functools import lru_cache
from pathlib import Path
from e4s_cl import logger
from e4s_cl.util import which, create_subprocess_exp

LOGGER = logger.get_logger(__name__)

@lru_cache
def host_libraries():
    """
    Output a dict containing all the host's linker cache in x86_64 format
    under the format {soname: path}
    """
    # The versions that appear in `ldconfig -p`
    # For some reason, ppc shows '64bits'
    valid_versions = {'64bit', 'x86-64'}

    ldconfig_path = which('ldconfig')
    if ldconfig_path is None:
        LOGGER.error("ldconfig executable not found")
        return {}

    with NamedTemporaryFile('r+') as custom:
        generation, _ = create_subprocess_exp(
            [ldconfig_path, '-C', custom.name], redirect_stdout=True)

        parsing, output = create_subprocess_exp(
            [ldconfig_path, '-C', custom.name, '-p'],
            log=False,
            redirect_stdout=True)

    if generation or parsing:
        LOGGER.error("Error getting libraries using %s", ldconfig_path)
        return {}

    _cache = {}

    for row in output.strip().split('\n')[1:]:
        # Expecting format "\t\tlibname.so.y (libc,arch) => /path/libname.so.y"
        pattern = r'^\s+(?P<soname>\S+(\.\S+)+).*\((?P<details>.*)\).*?(?P<path>(\/\S+)+)$'

        match = re.match(pattern, row)
        if not match:
            continue

        # Check the `arch` from above
        # Sometimes there is no data, so handle that case
        details = match.group('details').split(',')
        if len(details) < 2 or details[1] not in valid_versions:
            continue

        _cache[match.group('soname')] = match.group('path')

    return _cache

@lru_cache
def _linker_path():
    """
    Return linker search paths, in order
    Sourced from `man ld.so`
    """
    default_path = ['/lib', '/usr/lib', '/lib64', '/usr/lib64']
    ld_library_path = os.environ.get('LD_LIBRARY_PATH', "").split(':')

    return (ld_library_path, default_path)


def resolve(soname, rpath=None, runpath=None):
    """
    Get a path towards a library from a given soname.
    Implements system rules and takes the environment into account
    """

    found = None
    rpath = rpath or list()
    runpath = runpath or list()

    def _valid(path):
        return os.path.exists(path) and os.path.isdir(path)

    dynamic_paths = list(rpath) + _linker_path()[0] + list(runpath)
    default_paths = _linker_path()[1]

    for dir_ in filter(_valid, dynamic_paths):
        potential_lib = Path(dir_, soname).as_posix()
        if os.path.exists(potential_lib):
            found = potential_lib

    if not found and soname in host_libraries().keys():
        found = host_libraries()[soname]

    if not found:
        for dir_ in filter(_valid, default_paths):
            potential_lib = Path(dir_, soname).as_posix()
            if os.path.exists(potential_lib):
                found = potential_lib

    return os.path.realpath(found) if found else None
