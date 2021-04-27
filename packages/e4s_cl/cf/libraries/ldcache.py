import re
from e4s_cl.util import which, create_subprocess_exp
from e4s_cl.error import InternalError

# Dict with the host libraries, with sonames as keys, and paths as values
__HOST_LIBRARIES = {}


def host_libraries():
    """
    Output a dict containing all the host's linker cache in x86_64 format
    under the format {soname: path}
    """
    global __HOST_LIBRARIES

    if __HOST_LIBRARIES:
        return __HOST_LIBRARIES

    # The versions that appear in `ldconfig -p`
    # For some reason, ppc shows '64bits'
    valid_versions = {'64bits', 'x86-64'}

    ldconfig_path = which('ldconfig')
    if ldconfig_path is None:
        return __HOST_LIBRARIES

    retval, output = create_subprocess_exp([ldconfig_path, '-p'],
                                           redirect_stdout=True)

    if retval:
        raise InternalError("Error getting libraries using %s", ldconfig_path)

    for row in output.strip().split('\n')[1:]:
        # Expecting format "\t\tlibname.so.y (libc,arch) => /path/libname.so.y"
        pattern = '^\s+(?P<soname>\S+(\.\S+)+).*\((?P<details>.*)\).*?(?P<path>(\/\S+)+)$'

        m = re.match(pattern, row)
        if not m:
            continue

        # Check the `arch` from above
        # Sometimes there is no data, so handle that case
        details = m.group('details').split(',')
        if len(details) < 2 or 'OS' in details[1]:
            continue

        __HOST_LIBRARIES[m.group('soname')] = m.group('path')

    return __HOST_LIBRARIES
