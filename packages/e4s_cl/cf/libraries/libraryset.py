import re
from e4s_cl import logger
from e4s_cl.cf.libraries.linker import resolve
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


class Library:
    """
    Relevant ELF header fields used in the dynamic linking of libraries
    """
    def __init__(self, file=None, soname=""):
        self.soname = soname
        self.dyn_dependencies = set()
        self.required_versions = dict()
        self.defined_versions = set()

        self.rpath = []
        self.runpath = []
        self.binary_path = None

        if file:
            try:
                for section in ELFFile(file).iter_sections():
                    if isinstance(section, GNUVerDefSection):
                        self.__parseVerDef(section)
                    elif isinstance(section, GNUVerNeedSection):
                        self.__parseVerNeed(section)
                    elif isinstance(section, DynamicSection):
                        self.__parseDynamic(section)
            except ELFError as e:
                LOGGER.error("Error parsing '%s' for ELF data: %s", file.name,
                             e)

            self.binary_path = file.name

    def __parseDynamic(self, section):
        def __fetch_tags(id):
            return list(
                filter(lambda x: x.entry.d_tag == id, section.iter_tags()))

        tags = __fetch_tags('DT_SONAME')
        if len(tags) == 1:
            self.soname = tags[0].soname

        tags = __fetch_tags('DT_RPATH')
        if len(tags) == 1:
            self.rpath = tags[0].rpath.split(':')

        tags = __fetch_tags('DT_RUNPATH')
        if len(tags) == 1:
            self.runpath = tags[0].runpath.split(':')

        tags = __fetch_tags('DT_NEEDED')
        self.dyn_dependencies = {tag.needed for tag in tags}

    def __parseVerDef(self, section):
        self.defined_versions = {
            next(v_iter).name
            for _, v_iter in section.iter_versions()
        }

    def __parseVerNeed(self, section):
        needed = dict()

        for v, v_iter in section.iter_versions():
            needed[v.name] = {v.name for v in v_iter}

        self.required_versions = needed

    def __hash__(self):
        """
        hash method tying the ELFData object to the soname, to use in sets
        """
        return hash(self.soname + self.binary_path or '')

    def __eq__(self, other):
        if isinstance(other, Library):
            return self.soname == other.soname
        return NotImplemented


class HostLibrary(Library):
    pass


class GuestLibrary(Library):
    pass


class LibrarySet(set):
    @property
    def rpath(self):
        """
        -> list(str)
        Return a set of the libraries rpaths merged together
        """
        return flatten(map(lambda x: x.rpath, self))

    @property
    def runpath(self):
        """
        -> list(str)
        Return a set of the libraries runpaths merged together
        """
        return flatten(map(lambda x: x.runpath, self))

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
        return LibrarySet(self - self.required_libraries)

    @property
    def linkers(self):
        """
        -> LibrarySet, subset of self
        Returns a set of all linkers present in the set
        """
        return LibrarySet(filter(lambda x: not x.dyn_dependencies, self))

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
    def outdated_libraries(self):
        """
        -> LibrarySet, subset of self
        Sonames of libraries that do not implement all the symbols expected by
        the other libraries
        """
        outdated = LibrarySet()

        for library in self:
            for soname, required in library.required_versions.items():
                matches = set(filter(lambda x: x.soname == soname, self))

                if len(matches) != 1:
                    continue

                dependency = matches.pop()

                if required > dependency.defined_versions:
                    outdated.add(dependency)

        return outdated

    @property
    def complete(self):
        """
        -> bool
        Returns True if all the dependencies are resolved
        """
        return (len(self.missing_libraries) == 0
                and self.required_versions.issubset(self.defined_versions))

    def resolve(self, rpath=[], runpath=[]):
        """
        -> LibrarySet, superset of self
        will try to resolve all dynamic depedencies of the set's members, then
        add them to the returned set

        if the returned set complete() method returns False, a library cannot
        be found by e4s-cl
        """
        superset = LibrarySet(self)

        missing = superset.missing_libraries
        change = True

        while change:
            for soname in missing:
                path = resolve(soname,
                               rpath=superset.rpath + rpath,
                               runpath=superset.runpath + runpath)

                if not path:
                    continue

                with open(path, 'rb') as file:
                    superset.add(HostLibrary(file))

            change = superset.missing_libraries != missing
            missing = superset.missing_libraries

        return superset

    def trees(self, show_versions=False):
        """
        -> list(list(str))
        Returns a list of string lists. Each list contains lines that, when
        printed in succession, describe a dependency tree. Trees are calculated
        for every library in self.top_level.
        """
        def get_name(elem):
            header = color_text(elem.soname, 'red', None, ['bold'])

            if elem.binary_path:
                header = "%s (%s)" % (elem.soname, elem.binary_path)

            sections = []
            for soname, versions in elem.required_versions.items():
                for version in versions:
                    if not version in self.defined_versions:
                        version = color_text(version, 'red', None, ['bold'])
                    sections.append("├ %s (from %s)" % (version, soname))

            if sections and show_versions:
                header = "%s\n%s" % (header, "\n".join(sections))

            return header

        def gen_get_children():
            def get_children(elem):
                found = LibrarySet(
                    filter(lambda x: x.soname in elem.dyn_dependencies, self))

                not_found = elem.dyn_dependencies - found.sonames

                for name in not_found:
                    found.add(Library(soname=name))

                return found

            return get_children

        trees = []
        for lib in self.top_level:
            trees.append(
                format_tree(lib,
                            format_node=get_name,
                            get_children=gen_get_children()))

        return trees


def __LibraryDecoder(_type):
    def __LDecoder(obj):
        out = _type()

        for key, value in obj.items():
            setattr(out, key, value)

        return out

    return __LDecoder


JSON_HOOKS['Library'] = __LibraryDecoder(Library)
JSON_HOOKS['HostLibrary'] = __LibraryDecoder(HostLibrary)
JSON_HOOKS['GuestLibrary'] = __LibraryDecoder(GuestLibrary)
