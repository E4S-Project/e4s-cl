import re
from e4s_cl import logger
from e4s_cl.util import flatten, color_text, JSON_HOOKS

from elftools.common.exceptions import ELFError
from elftools.elf.elffile import ELFFile
from elftools.elf.dynamic import DynamicSection
from elftools.elf.gnuversions import (
    GNUVerDefSection,
    GNUVerNeedSection,
)

from tree_format import format_tree

LOGGER = logger.get_logger(__name__)


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
    def top_level(self):
        """
        -> LibrarySet, subset of self
        Returns a set of all libraries included in self that are not depended
        upon from another library in the set
        """
        return self - self.required_libraries

    @property
    def required_libraries(self):
        """
        -> LibrarySet, subset of self
        Returns a set of all libraries included in self that are depended
        upon from another library in the set
        """
        sonames = set(flatten(map(lambda x: x.dyn_dependencies, self)))
        return LibrarySet(filter(lambda x: x.soname in sonames, self))

    @property
    def sonames(self):
        """
        -> set(str)
        Returns a set with the sonames of all the libraries in self
        """
        return set(map(lambda x: x.soname, self))

    @property
    def missing_libraries(self):
        """
        -> set(str)
        Returns a set with the sonames of all the dependencies of the set's
        libraries not present in self
        """
        sonames = set(flatten(map(lambda x: x.dyn_dependencies, self)))
        return set(filter(lambda x: x not in self.sonames, sonames))

    @property
    def complete(self):
        """
        -> bool
        Returns True if all the dependencies are resolved
        """
        return (len(self.missing_libraries) == 0
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

