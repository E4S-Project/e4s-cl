"""Execute command

Definition of arguments and hooks related to the execute command,
file import calculations, and execution of a program passed as an
argument.
This command is used internally and thus cloaked from the UI
"""

from pathlib import Path
from e4s_cl import CONTAINER_DIR, CONTAINER_SCRIPT, EXIT_SUCCESS, E4S_CL_SCRIPT, logger, variables
from e4s_cl.error import InternalError
from e4s_cl.cli import arguments
from e4s_cl.cli.command import AbstractCommand
from e4s_cl.cf.template import Entrypoint
from e4s_cl.cf.containers import Container, BackendError
from e4s_cl.cf.libraries import libc_version, resolve, LibrarySet, HostLibrary, library_links

LOGGER = logger.get_logger(__name__)
_SCRIPT_CMD = Path(E4S_CL_SCRIPT).name

HOST_LIBS_DIR = Path(CONTAINER_DIR, 'hostlibs').as_posix()


def import_library(shared_object, container):
    """
    This method binds the shared object it got as an argument, along with all
    the symbolic links that may exist and point to the same file.

    This is because depending on the linker at compile-time some binaries
    require more or less precise versions of the same file (eg. libmpi.so for
    some and libmpi.so.12 for others). Binding all the references ensures the
    library is found down the line.
    """
    for file in library_links(shared_object):
        container.bind_file(file, Path(HOST_LIBS_DIR, file.name))


# pylint: disable=unused-argument
def filter_libraries(library_set, container, entrypoint):
    """ Library filter

    library_paths: list[pathlib.Path]
    container: e4s_cl.cf.containers.Container

    This method generates a LibarySet of libraries to import in the container.
    """

    guest_set = container.libraries
    filtered_set = LibrarySet(library_set)

    # Remove libc-tied libraries from the filtered set by adding the guest libraries
    for lib in library_set.glib:
        guest_lib = guest_set.find(lib.soname)
        if guest_lib:
            filtered_set.add(guest_lib)

    # Remove linkers from the import list
    for linker in guest_set.linkers:
        filtered_set.add(linker)

    # Print details on selected libraries as a tree
    for tree in filtered_set.trees(True):
        LOGGER.debug(tree)

    return LibrarySet(
        filter(lambda x: isinstance(x, HostLibrary), filtered_set))


def overlay_libraries(library_set, container, entrypoint):
    """ Library overlay

    library_paths: list[pathlib.Path]
    container: e4s_cl.cf.containers.Container

    This method selects all the libraries defined in the list, along with
    with the host's (implicitly newer) linker.
    """
    selected = LibrarySet(
        filter(lambda x: isinstance(x, HostLibrary), library_set))

    # Figure out what to if multiple linkers are required
    if len(library_set.linkers) != 1:
        raise InternalError("%d linkers detected. This should not happen." %
                            len(library_set.linkers))

    for linker in library_set.linkers:
        entrypoint.linker = Path(HOST_LIBS_DIR,
                                 Path(linker.binary_path).name).as_posix()
        container.bind_file(linker.binary_path,
                            dest=Path(HOST_LIBS_DIR,
                                      Path(linker.binary_path).name))

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

    host_newer = True
    guest_newer = False

    host_libc = libc_version()
    guest_libc = container.libc_v

    methods = {host_newer: overlay_libraries, guest_newer: filter_libraries}

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
                            type=str,
                            dest='image',
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
        except BackendError as err:
            return err.handle(type(err), err, None)

        params = Entrypoint()
        params.source_script_path = args.source

        # Analyze the host to get a thorough set of libraries required
        libset = LibrarySet.create_from(args.libraries, member=HostLibrary)

        # Analyze the container to get library information from the environment
        # it offers, using the entrypoint
        container.get_data(params, library_set=libset)

        params.command = args.cmd
        params.debug = logger.debug_mode()
        params.library_dir = HOST_LIBS_DIR

        if args.libraries:
            # Create a set of libraries to import
            libset = select_libraries(libset, container, params)

            for line in libset.ldd_format():
                LOGGER.debug(line)

            # Import each library along with all symlinks pointing to it
            for shared_object in libset:
                import_library(shared_object, container)

            # Preload the roots of all the set's trees
            def _path(library: HostLibrary):
                return Path(HOST_LIBS_DIR,
                            Path(library.binary_path).name).as_posix()

            for import_path in map(_path, libset.top_level):
                params.preload.append(import_path)

        if args.files:
            for path in args.files:
                container.bind_file(path)

        script_name = params.setup()

        container.bind_file(script_name, dest=CONTAINER_SCRIPT)

        command = [CONTAINER_SCRIPT]

        if variables.is_dry_run():
            LOGGER.info("Running %s in container %s", command, container)
            params.teardown()
            return EXIT_SUCCESS

        code, _ = container.run(command, redirect_stdout=False)

        params.teardown()

        return code


COMMAND = ExecuteCommand(
    __name__,
    summary_fmt=
    "Execute a command in a container with a tailor-made environment.")
