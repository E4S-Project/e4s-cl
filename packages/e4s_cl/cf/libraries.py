"""
Helpers linked to library manipulation
"""

import re
import pathlib
from e4s_cl import logger, util
from e4s_cl.util import which, create_subprocess_exp
from e4s_cl.error import InternalError

LOGGER = logger.get_logger(__name__)


def _parse_line(line):
    """
    Parse single line of ldd output.
    :param line: to parse
    :return: dictionnary with data, or empty if not available
    """
    found = not 'not found' in line
    parts = [part.strip() for part in line.split(' ')]

    if parts[0] != pathlib.Path(parts[0]).name and 'ld' in parts[0]:
        """
        More often than not, the linker will be shown with a line as such:
            /usr/lib64/ld-linux-x86-64.so.2
        While the other lines just have a soname as first field.
        Unfortunately some systems require the linker via ELF arcanes, and
        it shows as such:
            /usr/lib/ld-linux-x86-64.so.2 => /usr/lib64/ld-linux-x86-64.so.2
        This weeds the linker out, as one cannot reliably expect no `=>` to
        appear on linker lines.
        """
        return {'linker': {'path': parts[0], 'found': True}}

    # pylint: disable=line-too-long
    # There are two types of outputs for a dependency, with or without soname.
    # For example:
    # with soname: 'libstdc++.so.6 => /usr/lib/x86_64-linux-gnu/libstdc++.so.6 (0x00007f9a19d8a000)'
    # without soname: '/lib64/ld-linux-x86-64.so.2 (0x00007f9a1a329000)'
    # with soname but not found: 'libboost_program_options.so.1.62.0 => not found'
    # with soname but without path: 'linux-vdso.so.1 =>  (0x00007ffd7c7fd000)'
    # pylint: enable=line-too-long
    if '=>' in line:
        if len(parts) != 4:
            raise InternalError(
                "Expected 4 parts in the line but found {}: {}".format(
                    len(parts), line))

        soname = None
        dep_path = None

        if found:
            soname = parts[0]
            if parts[2] != '':
                dep_path = pathlib.Path(parts[2])
        else:
            if "/" in parts[0]:
                dep_path = pathlib.Path(parts[0])
            else:
                # No path
                return {}

        return {
            soname: {
                'path': dep_path.as_posix() if dep_path else None,
                'found': found
            }
        }

    if len(parts) != 2:
        raise InternalError(
            "Expected 2 parts in the line but found {}: {}".format(
                len(parts), line))

    # In this case, no soname was available
    return {}


def ldd(binary):
    """
    Run ldd on the binary passed as an argument
    """
    binary = pathlib.Path(binary).as_posix()

    command = "%(ldd)s %(binary)s" % {'ldd': which('ldd'), 'binary': binary}

    returncode, output = create_subprocess_exp(command.split(),
                                               redirect_stdout=True)

    if returncode:
        LOGGER.debug("Failed to determine %s's dynamic dependencies", binary)
        return {}

    libraries = {}  # type: Dict
    rows = filter(lambda x: x, [line.strip() for line in output.split('\n')])

    for line in rows:
        libraries.update(_parse_line(line=line))

    return libraries


# Dict with the host libraries, with sonames as keys, and paths as values
HOST_LIBRARIES = {}


def host_libraries():
    """
    Output a dict containing all the libraries available on the host,
    under the format {soname: path}
    """
    global HOST_LIBRARIES

    if HOST_LIBRARIES:
        return HOST_LIBRARIES

    ldconfig_path = util.which('ldconfig')

    if ldconfig_path is None:
        return HOST_LIBRARIES

    _, output = create_subprocess_exp([ldconfig_path, '-p'], redirect_stdout=True)

    for row in output.strip().split('\n')[1:]:
        # Expecting format "libname.so.y (lib,arch) => /path/libname.so.y"
        components = row.strip().split(' ')
        HOST_LIBRARIES[components[0]] = components[-1]

    return HOST_LIBRARIES


def extract_libc(text):
    """
    Extract libc version sumber from the output of ldd --version
    We could have used the libc but locating it would require some
    gymnastic, so accessing ldd seemed cleaner.
    """

    # The first line of output is usually:
    # > ldd (<noise with numbers>) x.y
    if not text:
        LOGGER.error("Failed to determine libc version from '%s'", text)
        return (0, 0, 0)

    try:
        version_string = text.split('\n')[0].split()[-1]
    except IndexError:
        LOGGER.error("Failed to determine libc version from '%s'", text)
        return (0, 0, 0)

    return tuple([int(val) for val in re.findall(r'\d+', version_string)])


HOST_LIBC = None


def libc_version():
    """
    Get the version number of the libc available on the host
    Caches the result
    """

    global HOST_LIBC

    if HOST_LIBC:
        return HOST_LIBC

    executable = which('ldd')
    ret, out = create_subprocess_exp([executable, '--version'],
                                     redirect_stdout=True)
    if ret:
        LOGGER.error("Could not determine the libc version")
        HOST_LIBC = (0, 0, 0)

    else:
        HOST_LIBC = extract_libc(out)

    return HOST_LIBC
