"""
Library analysis and manipulation helpers
"""

import re
import pathlib
from e4s_cl import logger, util
from e4s_cl.util import which, create_subprocess_exp, flatten, color_text, JSON_HOOKS
from e4s_cl.error import InternalError

from elftools.common.exceptions import ELFError
from elftools.elf.elffile import ELFFile
from elftools.elf.dynamic import DynamicSection
from elftools.elf.gnuversions import (
    GNUVerDefSection,
    GNUVerNeedSection,
)

from tree_format import format_tree

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

    _, output = create_subprocess_exp([ldconfig_path, '-p'],
                                      redirect_stdout=True)

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


class ELFData:
    """
    Relevant ELF header fields used in the dynamic linking of libraries
    """
    def __init__(self):
        self.soname = ""
        self.dyn_dependencies = set()
        self.required_versions = {}
        self.defined_versions = set()

    def __hash__(self):
        """
        hash method tying the ELFData object to the soname, to use in sets
        """
        return hash(self.soname)

    def __eq__(self, other):
        if isinstance(other, ELFData):
            return self.soname == other.soname
        return NotImplemented


def parseELF(file):
    """
    Create ELFData from an opened shared binary.
    The file argument must be opened in byte mode !
    """
    library = ELFData()

    def parseDynamic(section):
        tags = list(
            filter(lambda x: x.entry.d_tag == 'DT_SONAME',
                   section.iter_tags()))

        if len(tags) == 1:
            library.soname = tags[0].soname

        tags = filter(lambda x: x.entry.d_tag == 'DT_NEEDED',
                      section.iter_tags())

        library.dyn_dependencies = {tag.needed for tag in tags}

    def parseVerDef(section):
        library.defined_versions = {
            next(v_iter).name
            for _, v_iter in section.iter_versions()
        }

    def parseVerNeed(section):
        needed = {}

        for v, v_iter in section.iter_versions():
            needed[v.name] = [v.name for v in v_iter]

        library.required_versions = needed

    try:
        for section in ELFFile(file).iter_sections():
            if isinstance(section, GNUVerDefSection):
                parseVerDef(section)
            elif isinstance(section, GNUVerNeedSection):
                parseVerNeed(section)
            elif isinstance(section, DynamicSection):
                parseDynamic(section)
    except ELFError as e:
        LOGGER.error("%s error:" % file.name, e, file=sys.stderr)

    return library


class LibrarySet(set):
    @property
    def defined_versions(self):
        return set(flatten(map(lambda x: x.defined_versions, self)))

    @property
    def required_versions(self):
        return set(
            flatten(flatten(map(lambda x: x.required_versions.values(),
                                self))))

    @property
    def required_libraries(self):
        sonames = set(flatten(map(lambda x: x.dyn_dependencies, self)))
        return LibrarySet(filter(lambda x: x.soname in sonames, self))

    @property
    def sonames(self):
        return set(map(lambda x: x.soname, self))

    @property
    def top_level(self):
        return self - self.required_libraries

    @property
    def complete(self):
        return (self.required_libraries.issubset(self)
                and self.required_versions.issubset(self.defined_versions))

    def trees(self):
        def get_name(elem):
            if getattr(elem, 'found', True):
                return elem.soname
            return color_text(elem.soname, 'red', None, ['bold'])

        def gen_get_children():
            def get_children(elem):
                found = LibrarySet(
                    filter(lambda x: x.soname in elem.dyn_dependencies, self))

                not_found = elem.dyn_dependencies - found.sonames

                for name in not_found:
                    mock = ELFData()
                    mock.soname = name
                    mock.found = False

                    found.add(mock)

                return found

            return get_children

        trees = []
        for lib in self.top_level:
            trees.append(
                format_tree(lib,
                            format_node=get_name,
                            get_children=gen_get_children()))

        return trees

def ELFDataFromDict(obj):
    out = ELFData()

    for key, value in obj.items():
        setattr(out, key, value)

    return out

JSON_HOOKS['ELFData'] = ELFDataFromDict
