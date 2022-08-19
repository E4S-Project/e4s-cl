"""Execute command

Definition of arguments and hooks related to the execute command,
file import calculations, and execution of a program passed as an
argument.
This command is used internally and thus cloaked from the UI
"""

from typing import Union
from pathlib import Path
from sotools.linker import resolve
from sotools.libraryset import LibrarySet, Library
from e4s_cl import (EXIT_SUCCESS, E4S_CL_SCRIPT, logger, variables)
from e4s_cl.util import which
from e4s_cl.error import InternalError
from e4s_cl.cli import arguments
from e4s_cl.cli.command import AbstractCommand
from e4s_cl.cf.template import Entrypoint
from e4s_cl.cf.containers import Container, FileOptions
from e4s_cl.cf.libraries import (libc_version, library_links)
from e4s_cl.cf.wi4mpi import (wi4mpi_enabled, wi4mpi_root, wi4mpi_import,
                              wi4mpi_libraries, wi4mpi_libpath, wi4mpi_preload)

LOGGER = logger.get_logger(__name__)
_SCRIPT_CMD = Path(E4S_CL_SCRIPT).name


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
        container.bind_file(file, Path(container.import_library_dir,
                                       file.name))


# pylint: disable=unused-argument
def filter_libraries(library_set, container, entrypoint):
    """ Library filter

    library_paths: list[pathlib.Path]
    container: e4s_cl.cf.containers.Container

    This method filters out libraries that may cause problems when imported
    in a newer glibc environment
    """

    filtered_set = LibrarySet(library_set)

    # Remove libc-tied libraries from the filtered set, including the linker
    for lib in library_set.glib:
        filtered_set.remove(lib)

    return filtered_set


def overlay_libraries(library_set, container, entrypoint):
    """ Library overlay

    library_paths: list[pathlib.Path]
    container: e4s_cl.cf.containers.Container
    entrypoint: e4s_cl.cf.template.Entrypoint

    This method binds the libraries defined in the set, along with
    with the host's (implicitly newer) glib library suite and a bash binary
    to enable running scripts.

    Those bounds are necessary to run libraries that might depend on the more
    recent libraries of the host. glib binaries often use private symbols that
    are version dependent (GLIBC_PRIVATE) and this step ensures a match.
    """

    # Determine what the host's bash binary depends on
    full = LibrarySet.create_from([which('bash')])
    bash_binary = full.top_level
    bash_requirements = full - bash_binary

    # Hardcoded glib libraries sonames
    glib_sonames = [
        'libcrypt.so.1', 'libc.so.6', 'libm.so.6', 'libmvec.so.1',
        'libnsl.so.1', 'libnss_compat.so.2', 'libnss_db.so.2',
        'libnss_dns.so.2', 'libnss_files.so.2', 'libnss_hesiod.so.2',
        'libpthread.so.0', 'libresolv.so.2', 'librt.so.1'
    ]
    # Find the available libraries on the host, and bundle them in a set
    paths = filter(None, map(resolve, glib_sonames))
    glib_set = LibrarySet.create_from(paths)

    # Import the bash binary in the container
    entrypoint.interpreter = Path(container.import_binary_dir,
                                  'bash').as_posix()
    container.bind_file(bash_binary.pop().binary_path,
                        dest=entrypoint.interpreter)

    # Import the library set passed as an argument along with the bash
    # dependencies and the host's glib
    selected = LibrarySet(library_set | bash_requirements | glib_set)

    # Figure out what to if multiple linkers are required
    if len(selected.linkers) != 1:
        raise InternalError(
            f"{len(selected.linkers)} linkers detected. This should not happen."
        )

    # Override linkers in the container
    for linker in selected.linkers:
        entrypoint.linker = Path(container.import_binary_dir,
                                 Path(linker.binary_path).name).as_posix()
        container.bind_file(linker.binary_path, dest=entrypoint.linker)

    # Override the container's glib with the host's
    for lib in selected.glib | glib_set:
        if lib.soname in container.cache:
            LOGGER.debug("Overriding guest `%s` with host `%s`",
                         container.cache[lib.soname], lib.binary_path)
            container.bind_file(lib.binary_path,
                                dest=container.cache[lib.soname])

    # Remove all the glib libraries from the import list as they have been
    # bound above
    return LibrarySet(selected - glib_set)


def select_libraries(library_set, container, entrypoint):
    """ Select the libraries to make available in the future container

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

    # Analyze the container to get glibc information
    container.get_data()
    guest_libc = container.libc_v
    host_libc = libc_version()

    methods = {host_newer: overlay_libraries, guest_newer: filter_libraries}

    host_precedence = host_libc > guest_libc

    LOGGER.debug("Host libc: %s %s Guest libc: %s", str(host_libc),
                 '>' if host_precedence else '<=', str(guest_libc))

    selected_libraries = methods[host_precedence](library_set, container,
                                                  entrypoint)

    for line in selected_libraries.ldd_format():
        LOGGER.debug(line)

    return selected_libraries


def generate_rtld_path(container):
    """
    Create the final path list to be passed to LD_LIBRARY_PATH in the container
    """
    path_list = []

    if wi4mpi_enabled():
        wi4mpi_paths = list(
            map(lambda x: x.as_posix(), wi4mpi_libpath(wi4mpi_root())))

        path_list += wi4mpi_paths

    if hasattr(container.__class__, 'linker_path'):
        path_list += container.__class__.linker_path

    return path_list + [container.import_library_dir]


def _check_access(path: Union[Path, str]) -> bool:
    check = Path(path).exists()

    if not check:
        LOGGER.debug("Omitting file '%s' from bind list: file not found",
                     Path(path).as_posix())

    return check


class ExecuteCommand(AbstractCommand):
    """``execute`` subcommand."""

    def _construct_parser(self):
        usage = f"{self.command} [arguments] <command> [command_arguments]"
        parser = arguments.get_parser(prog=self.command,
                                      usage=usage,
                                      description=self.summary)
        parser.add_argument("--backend",
                            type=str,
                            dest='backend',
                            required=True,
                            help="Specify the backend name",
                            metavar='backend')

        parser.add_argument('--image',
                            type=str,
                            dest='image',
                            required=True,
                            help="Container image to use",
                            metavar='image')

        parser.add_argument('--files',
                            type=arguments.posix_path_list,
                            help="Files to bind, comma-separated",
                            default=[],
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

        # This object automatically mutates to one of the defined container
        # classes, and holds information about what is bound to the future
        # container launch
        container = Container(name=args.backend, image=args.image)

        # All execute does is build this object that translates to a bash
        # script, that is then bound to the container to be executed
        params = Entrypoint()

        # If WI4MPI is enabled, analyze the libraries it uses
        required_libraries = args.libraries + wi4mpi_libraries(wi4mpi_root())

        # The following is a set of all libraries required. It
        # is used in the container to check version mismatches
        libset = LibrarySet.create_from(required_libraries)
        if libset:
            # Analyze the container to get library information from the environment
            # it offers, using the entrypoint and the above libraries
            container.get_data()

        # Bind all accessible requested files
        for path in filter(_check_access, args.files or []):
            container.bind_file(path, option=FileOptions.READ_WRITE)

        # This script is sourced before any other command in the container
        params.source_script_path = args.source

        # Setup the final command and metadata relating to the execution
        params.command = args.cmd
        params.debug = logger.debug_mode()
        params.linker_library_path = generate_rtld_path(container)

        # Create a set of libraries to import using a library_set object,
        # then filtering it according to the contents of the container
        final_libset = select_libraries(libset, container, params)

        # Import each library along with all symlinks pointing to it
        for shared_object in final_libset:
            import_library(shared_object, container)

        if not wi4mpi_enabled():
            # Preload the top-level libraries of the imported set to bypass
            # any potential RPATH settings
            def _path(library: Library):
                return Path(container.import_library_dir,
                            Path(library.binary_path).name).as_posix()

            for imported_library_path in map(_path, final_libset.top_level):
                params.preload.append(imported_library_path)
        else:
            # If WI4MPI is found in the environment, import its files and
            # preload its required components
            wi4mpi_import(container, wi4mpi_root())

            params.preload += wi4mpi_preload(wi4mpi_root())

        # Write the entry script to a file, then bind it to the container
        script_name = params.setup()
        container.bind_file(script_name, dest=container.script)

        command = [container.script]

        if variables.is_dry_run():
            LOGGER.info("Running %s in container %s", command, container)
            params.teardown()
            return EXIT_SUCCESS

        code = container.run(command)

        if code:
            LOGGER.critical("Container command failed with error code %d",
                            code)

        params.teardown()

        return code


COMMAND = ExecuteCommand(
    __name__,
    summary_fmt=
    "Execute a command in a container with a tailor-made environment.")
