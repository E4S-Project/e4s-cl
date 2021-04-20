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

    return cache.resolve()


def import_library(shared_object, container):
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

    if not isinstance(so, HostLibrary):
        raise InternalError("Wrong argument type for import_libraries: %s" %
                            type(so))

    libname = Path(so.binary_path).name.split('.so')
    library_file = so.binary_path
    cleared = []

    if not libname or len(libname) < 2:
        LOGGER.error("Invalid name: %s", so.soname)

    for file in list(Path(so.binary_path).parent.glob("%s.so*" % libname[0])):
        if os.path.realpath(file) == library_file:
            cleared.append(file)

    for file in cleared:
        container.bind_file(file, Path(HOST_LIBS_DIR, file.name), options='ro')


def filter_libraries(library_set, container, entrypoint):
    """ Library filter

    library_paths: list[pathlib.Path]
    container: e4s_cl.cf.containers.Container

    This method selects all the libraries not present in the container,
    as they would trigger symbol issues when used with the container's
    linker.
    """



    raise NotImplementedError("Library filtering has to be implemented")


def overlay_libraries(library_set, container, entrypoint):
    """ Library overlay

    library_paths: list[pathlib.Path]
    container: e4s_cl.cf.containers.Container

    This method selects all the libraries defined in the list, along with
    with the host's (implicitly newer) linker.
    """
    selected = LibrarySet(
        filter(lambda x: x.isinstance(x, HostLibrary), library_set))

    # Resolve linkers actual paths. This now contains paths to all the linkers
    # required to load the entire dependency tree.
    host_linkers = {l for l in library_set.linkers}

    # Figure out what to if multiple linkers are required
    if len(host_linkers) != 1:
        raise InternalError("%d linkers detected. This should not happen." %
                            len(host_linkers))

    for linker in host_linkers:
        entrypoint.linker = Path(HOST_LIBS_DIR, Path(linker.binary_path).name)
        container.bind_file(linker,
                            dest=Path(HOST_LIBS_DIR,
                                      Path(linker.binary_path).name),
                            options='ro')

    return selected


def select_libraries(library_set, container, entrypoint):
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

    host_libc = libc_version()
    guest_libc = container.libc_v

    methods = {HOST_NEWER: overlay_libraries, GUEST_NEWER: filter_libraries}

    host_precedence = host_libc > guest_libc

    LOGGER.debug("Host libc: %s / Guest libc: %s", str(host_libc),
                 str(guest_libc))

    return methods[host_precedence](library_set, container, entrypoint)


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

        libset = create_set(args.libraries)
        container.get_data(params, library_set=libset)

        params.command = args.cmd
        params.library_dir = HOST_LIBS_DIR

        if args.libraries:
            for so in select_libraries(libset, container, params):
                import_library(so, container)

        if args.files:
            for path in args.files:
                container.bind_file(path, options='ro')

        script_name = params.setUp()

        command = [script_name]

        if variables.is_dry_run():
            LOGGER.info("Running %s in container %s", command, container)
            params.tearDown()
            return EXIT_SUCCESS

        code, _ = container.run(command, redirect_stdout=False)

        params.tearDown()

        return EXIT_SUCCESS


COMMAND = ExecuteCommand(
    __name__,
    summary_fmt=
    "Execute a command in a container with a tailor-made environment.")
