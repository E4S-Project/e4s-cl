"""Execute command

Definition of arguments and hooks related to the execute command,
file import calculations, and execution of a program passed as an
argument.
"""

import os
from pathlib import Path
from argparse import ArgumentTypeError
from e4s_cl import EXIT_SUCCESS, EXIT_FAILURE, E4S_CL_SCRIPT, logger, variables
from e4s_cl.error import InternalError
from e4s_cl.util import json_loads
from e4s_cl.cli import arguments
from e4s_cl.cli.command import AbstractCommand
from e4s_cl.cli.commands.analyze import COMMAND as analyzeCommand
from e4s_cl.cf.template import Entrypoint
from e4s_cl.cf.containers import Container, BackendNotAvailableError
from e4s_cl.cf.libraries import ldd, libc_version, resolve, LibrarySet, HostLibrary

LOGGER = logger.get_logger(__name__)
_SCRIPT_CMD = Path(E4S_CL_SCRIPT).name

HOST_LIBS_DIR = Path('/hostlibs/').as_posix()


def create_set(library_list):
    """
    Given a list of strings, create a cf.libraries.LibrarySet with all the
    dependencies resolved
    """

    cache = LibrarySet()

    for element in library_list:
        if isinstance(element, Path):
            path = element.as_posix()
        elif isinstance(element, str):
            if '/' in element:
                path = Path(element).as_posix()
            else:
                path = resolve(element,
                               rpath=cache.rpath,
                               runpath=cache.runpath)
        else:
            LOGGER.error("Unresolved library: '%s'", element)

        with open(path, 'rb') as file:
            cache.add(HostLibrary(file))

    missing = cache.missing_libraries
    change = True

    while change:
        for soname in cache.missing_libraries:
            path = resolve(soname, rpath=cache.rpath, runpath=cache.runpath)

            if not path:
                continue

            with open(path, 'rb') as file:
                cache.add(HostLibrary(file))

        change = cache.missing_libraries != missing
        missing = cache.missing_libraries

    return cache


def analyze_container(container, libset, entrypoint):
    """
    Run the e4s-cl analyze command in the container to analyze the environment
    inside of it. The results will be used to tailor the library import
    to ensure compatibility of the shared objects.
    """
    fdr, fdw = os.pipe()
    os.set_inheritable(fdw, True)
    container.bind_env_var('__E4S_CL_JSON_FD', str(fdw))

    entrypoint.command = [E4S_CL_SCRIPT, 'analyze', '--libraries'] + list(
        libset.sonames)
    script_name = entrypoint.setUp()

    container.run([script_name], redirect_stdout=True)

    entrypoint.tearDown()

    return json_loads(os.read(fdr, 1024**3).decode())


def import_library(shared_object_path, container):
    """
    End import method

    This method binds the shared object it got as an argument, along with all
    the symbolic links that may exist and point to the same file.

    Given the directory:
    lrwxrwxrwx. 1 root root   16 May 13  2019 libmpi.so -> libmpi.so.12.1.1
    lrwxrwxrwx. 1 root root   16 May 13  2019 libmpi.so.12 -> libmpi.so.12.1.1
    -rwxr-xr-x. 1 root root 2.7M May 13  2019 libmpi.so.12.1.1

    If any of those 3 files were to be passed as an argument, all would be
    selected to be bound.

    This is because depending on the linker at compile-time some binaries
    require more or less precise versions of the same file (eg. libmpi.so for
    some and libmpi.so.12 for others). Binding all the references ensures the
    library is found down the line.
    """

    if not isinstance(shared_object_path, Path):
        shared_object_path = Path(shared_object_path)

    libname = shared_object_path.name.split('.so')
    library_file = os.path.realpath(shared_object_path)
    cleared = []

    if not libname:
        LOGGER.error("Invalid name: %s", shared_object_path.as_posix())

    for file in list(shared_object_path.parent.glob("%s.so*" % libname[0])):
        if os.path.realpath(file) == library_file:
            cleared.append(file)

    for file in cleared:
        container.bind_file(file, Path(HOST_LIBS_DIR, file.name), options='ro')


def filter_libraries(library_paths, container, entrypoint):
    """ Library filter

    library_paths: list[pathlib.Path]
    container: e4s_cl.cf.containers.Container

    This method selects all the libraries not present in the container,
    as they would trigger symbol issues when used with the container's
    linker.
    """
    # Compute the list of sonames available in the container
    selected = {}

    for path in library_paths:
        # Use a ldd parser to grab all the dependencies of
        # the requested library
        # format:
        #   { name(str): path(str) }
        dependencies = ldd(path)

        # Add the library itself as a potential import
        dependencies.update({path.name: {'path': path.as_posix()}})

        dependencies.pop('linker')

        for soname, info in dependencies.items():
            # Add if not present in the container but present on the host
            if (soname not in container.libraries.keys()) and info.get('path'):
                selected.update({soname: info.get('path')})

    return selected.values()


def overlay_libraries(library_paths, container, entrypoint):
    """ Library overlay

    library_paths: list[pathlib.Path]
    container: e4s_cl.cf.containers.Container

    This method selects all the libraries defined in the list, along with
    with the host's (implicitly newer) linker.
    """
    selected = {}
    linkers = []

    for path in library_paths:
        # Use a ldd parser to grab all the dependencies of
        # the requested library
        # format:
        #   { name(str): path(str) }
        dependencies = ldd(path)

        # Add the library itself as a potential import
        dependencies.update({path.name: {'path': path.as_posix()}})

        # Don't bind the linker as a library
        linkers.append(dependencies.pop('linker')['path'])

        for soname, info in dependencies.items():
            selected.update({soname: info.get('path')})

    # Resolve linkers actual paths. This now contains paths to all the linkers
    # required to load the entire dependency tree.
    host_linkers = {Path(os.path.realpath(linker)) for linker in linkers}

    # Figure out what to if multiple linkers are required
    if len(host_linkers) != 1:
        raise InternalError(
            "Mutliple or no linkers detected. This should not happen.")
    """
    # Override every linker on the container
    for linker in container.linkers:
        LOGGER.debug("Overwriting linker: %s => %s", host_linkers[0], linker)
        container.bind_file(host_linkers[0], dest=linker, options='ro')
        """

    for linker in host_linkers:
        entrypoint.linker = Path(HOST_LIBS_DIR, linker.name)
        container.bind_file(linker,
                            dest=Path(HOST_LIBS_DIR, linker.name),
                            options='ro')

    return selected.values()


def select_libraries(library_paths, container, entrypoint):
    """ Select the libraries to make available in the future container

    library_paths: list[pathlib.Path]

    This method checks the libc versions compatibilities and returns a
    list of libraries safe to bind dependending on that check.

    If the container's linker is more recent than the hosts, it must be used.
    libc.so's version must equals the linker's. Some libraries must be bound,
    some must not as they exist in the container, tied to its linker.
     => filter_libraries

    However, if the host linker is newer, the host libc is newer, and libraries
    fail if used with the older libc of the container. We must then bind it,
    but binding libc implies binding the linker too, as both need to match.
    In the process, we bind all the necessary libraries.
     => overlay_libraries

    Why not overlay in both cases you ask ? As we run container-compiled
    binaries, they expect a minimal version of libc. It is fine to run with
    a newer libc, but very hazardous to run with an older one.
    """

    HOST_NEWER = True
    GUEST_NEWER = False

    def compare_versions(host_ver, container_ver):
        for host, container in zip(host_ver, container_ver):
            if host > container:
                return HOST_NEWER
            elif host < container:
                return GUEST_NEWER

        # By default, better to overlay
        return HOST_NEWER

    methods = {HOST_NEWER: overlay_libraries, GUEST_NEWER: filter_libraries}

    host_precedence = libc_version() > container.libc_version

    LOGGER.debug("Host libc: %s / Guest libc: %s", str(libc_version()),
                 str(container.libc_version))

    return methods[host_precedence](library_paths, container, entrypoint)


class ExecuteCommand(AbstractCommand):
    """``execute`` subcommand."""
    def _construct_parser(self):
        usage = "%s [arguments] <command> [command_arguments]" % self.command
        parser = arguments.get_parser(prog=self.command,
                                      usage=usage,
                                      description=self.summary)
        parser.add_argument("--backend",
                            type=str,
                            dest='backend',
                            required=True,
                            help="Specify the container executable",
                            metavar='executable')

        parser.add_argument('--image',
                            type=arguments.existing_posix_path,
                            required=True,
                            help="Container image to use",
                            metavar='image')

        parser.add_argument('--files',
                            type=arguments.existing_posix_path_list,
                            help="Files to bind, comma-separated",
                            metavar='files')

        parser.add_argument('--libraries',
                            type=arguments.existing_posix_path_list,
                            help="Libraries to bind, comma-separated",
                            default=[],
                            metavar='libraries')

        parser.add_argument('--source',
                            type=arguments.existing_posix_path,
                            help="Script to source",
                            metavar='libraries')

        parser.add_argument('cmd',
                            type=str,
                            help="Executable command, e.g. './a.out'",
                            metavar='command',
                            nargs=arguments.REMAINDER)

        return parser

    def main(self, argv):
        args = self._parse_args(argv)

        try:
            container = Container(executable=args.backend, image=args.image)
        except BackendNotAvailableError:
            self.parser.error("Executable %s not available" % args.backend)
            return EXIT_FAILURE

        params = Entrypoint()
        params.source_script_path = args.source
        params.command = args.cmd
        params.library_dir = HOST_LIBS_DIR

        if args.libraries:
            for local_path in select_libraries(args.libraries, container,
                                               params):
                import_library(local_path, container)

        if args.files:
            for path in args.files:
                container.bind_file(path, options='ro')

        script_name = params.setUp()

        command = [script_name]

        if variables.is_dry_run():
            LOGGER.info("Running %s in container %s", command, container)
            params.tearDown()
            return EXIT_SUCCESS

        container.run(command, redirect_stdout=False)

        params.tearDown()

        return EXIT_SUCCESS


COMMAND = ExecuteCommand(
    __name__,
    summary_fmt=
    "Execute a command in a container with a tailor-made environment.")
