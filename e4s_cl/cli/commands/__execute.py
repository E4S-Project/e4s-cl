"""Execute command

Definition of arguments and hooks related to the execute command,
file import calculations, and execution of a program passed as an
argument.
This command is used internally and thus cloaked from the UI
"""

import os
from typing import Union, List
from pathlib import Path
import re 
from sotools.linker import resolve
from sotools.libraryset import LibrarySet, Library
from e4s_cl import (
    E4S_CL_SCRIPT,
    EXIT_SUCCESS,
    config,
    logger,
    variables,
)
from e4s_cl.util import which
from e4s_cl.error import InternalError
from e4s_cl.cli import arguments
from e4s_cl.cli.command import AbstractCommand
from e4s_cl.cf.template import Entrypoint
from e4s_cl.cf.containers import Container, FileOptions
from e4s_cl.cf.libraries import (libc_version, library_links)
from e4s_cl.cf.wi4mpi import (
    wi4mpi_import,
    wi4mpi_libpath,
    wi4mpi_libraries,
    wi4mpi_preload,
    wi4mpi_root,
)

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
        'libc.so.6',
        'libdl.so.2',
        'libcrypt.so.1',
        'libm.so.6',
        'libmvec.so.1',
        'libnsl.so.1',
        'libnss_compat.so.2',
        'libnss_db.so.2',
        'libnss_dns.so.2',
        'libnss_files.so.2',
        'libnss_hesiod.so.2',
        'libpthread.so.0',
        'libresolv.so.2',
        'librt.so.1',
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


def generate_rtld_path(container: Container,
                       wi4mpi_install_dir: Path) -> List[Path]:
    """
    Create the final path list to be passed to LD_LIBRARY_PATH in the container
    """
    path_list = []

    if wi4mpi_install_dir is not None:
        wi4mpi_paths = list(
            map(lambda x: x.as_posix(), wi4mpi_libpath(wi4mpi_install_dir)))

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


# ------------------- MPICH-family aliasing (no OMPI) -------------------

# Families we support for aliasing (MPICH lineage, including Cray)
# - C MPI:      libmpi.so.*, libmpi_cray.so.*
# - Fortran:    libmpifort.so.*, libmpifort_cray.so.*
# - C++ MPI:    libmpicxx.so.*, libmpi_cxx.so.*
#
# Explicitly excluded (Open MPI):
# - libmpi.so.4X (e.g., .40, .41, ...)
# - libmpi_{mpifh,usempi,usempif08}.so.*
_MPI_FAMILY_PATTERNS = {
    'mpi': re.compile(r'^libmpi(?:_cray)?\.so(?:\.(?!4[0-9])\d+)*$'),
    'mpifort': re.compile(r'^libmpifort(?:_cray)?\.so(?:\.\d+)*$'),
    'mpicxx': re.compile(r'^(?:libmpicxx|libmpi_cxx)\.so(?:\.\d+)*$'),
}
# Open MPI exclusions
_OMPI_MPI_RE = re.compile(r'^libmpi\.so\.4[0-9]+$')
_OMPI_FORTRAN_SPLIT_RE = re.compile(
    r'^libmpi_(?:mpifh|usempi|usempif08)\.so(?:\.\d+)*$')


def _which_mpi_family(name: str) -> str:
    for fam, pat in _MPI_FAMILY_PATTERNS.items():
        if pat.match(name):
            return fam
    return ''


def _lib_name_candidates(lib: Library) -> List[str]:
    """
    Return candidate names to classify a Library (prefer soname, fallback to filename).
    """
    names = []
    try:
        if lib.soname:
            names.append(lib.soname)
    except AttributeError:
        pass
    names.append(Path(lib.binary_path).name)
    return names


def alias_guest_mpi_sonames_conservative(library_set: LibrarySet,
                                         container: Container) -> None:
    """
    Bind additional alias filenames for MPICH-family MPI libs into the import dir,
    matching guest SONAMEs from the container's ld.so.cache. Excludes Open MPI.

    For each host library in a supported family (mpi, mpifort, mpicxx), and for
    each guest SONAME in the same family, bind:
      origin: <host lib path>
      dest:   /.e4s-cl/hostlibs/<guest SONAME>

    This ensures the guest loader resolves its expected SONAME to the host file.
    """
    if not container.cache:
        return

    # Build guest SONAMEs by family from ld.so.cache keys, excluding Open MPI
    guest_by_family = {fam: [] for fam in _MPI_FAMILY_PATTERNS.keys()}
    for soname in container.cache.keys():
        # Skip Open MPI variants explicitly
        if _OMPI_MPI_RE.match(soname) or _OMPI_FORTRAN_SPLIT_RE.match(soname):
            continue
        fam = _which_mpi_family(soname)
        if fam:
            guest_by_family[fam].append(soname)

    # For each host lib in the set, classify and alias to matching guest SONAMEs
    for lib in library_set:
        host_family = ''
        for candidate in _lib_name_candidates(lib):
            host_family = _which_mpi_family(candidate)
            if host_family:
                break
        if not host_family:
            continue  # not an MPI lib we manage

        guest_names = guest_by_family.get(host_family, [])
        if not guest_names:
            continue

        for gname in guest_names:
            dest = Path(container.import_library_dir, gname)
            LOGGER.debug("Aliasing host '%s' as guest '%s' at '%s'",
                         lib.binary_path, gname, dest)
            container.bind_file(lib.binary_path, dest=dest)


def _alias_wi4mpi_fake_libs_for_guest(wi4mpi_install_dir: Path,
                                      container: Container) -> None:
    """
    When using Wi4MPI, bind fake MPI libraries with guest SONAME aliases.
    
    Wi4MPI provides fake libraries (e.g., libmpi.so.12) that need to be accessible
    with MPICH-specific names (e.g., libmpich.so.12, libmpichfort.so.12) so that
    container binaries linked to MPICH can find them.
    
    This creates bindings so that guest MPI SONAMEs resolve to Wi4MPI fake libraries.
    """
    # Get the Wi4MPI FROM parameter to determine which fake library directory to use
    from_family = os.environ.get("WI4MPI_FROM", "").upper()
    
    if not from_family:
        LOGGER.debug("WI4MPI_FROM not set; skipping fake library aliasing")
        return
    
    LOGGER.debug("Wi4MPI fake lib aliasing: from_family=%s", from_family)
    fakelib_dir = wi4mpi_install_dir / 'libexec' / 'wi4mpi' / f"fakelib{from_family}"
    
    if not fakelib_dir.exists():
        LOGGER.warning("Wi4MPI fakelib directory not found: %s", fakelib_dir)
        return
    
    LOGGER.debug("Wi4MPI fake lib aliasing: fakelib_dir=%s", fakelib_dir)
    
    # Mapping from generic MPI library names to MPICH-specific names
    # Wi4MPI provides libmpi.so.*, libmpifort.so.*, etc.
    # MPICH uses libmpich.so.*, libmpichfort.so.*, etc.
    name_mappings = {
        'libmpi.so': ['libmpich.so', 'libmpi.so'],
        'libmpifort.so': ['libmpichfort.so', 'libmpifort.so'],
        'libmpicxx.so': ['libmpichcxx.so', 'libmpicxx.so'],
    }
    
    # Bind Wi4MPI fake libraries with appropriate SONAME aliases for MPICH
    # This ensures binaries linked to libmpich.so.X find the Wi4MPI translation layer
    for wi4mpi_base, target_bases in name_mappings.items():
        # Find all Wi4MPI fake libraries matching this base (e.g., libmpi.so.12, libmpi.so.4)
        fake_libs = list(fakelib_dir.glob(f"{wi4mpi_base}*"))
        if not fake_libs:
            continue
        
        for fake_lib in fake_libs:
            # Extract version suffix (e.g., ".12" from "libmpi.so.12")
            fake_name = fake_lib.name
            if '.' in fake_name and fake_name.count('.') >= 2:
                # Get suffix after base name (e.g., ".12" from "libmpi.so.12")
                suffix_start = fake_name.find('.', fake_name.find('.') + 1)
                suffix = fake_name[suffix_start:]
                
                # Create aliases for each target base name
                for target_base in target_bases:
                    target_soname = f"{target_base}{suffix}"
                    # Always create alias for MPICH variants when translating from MPICH
                    dest = Path(container.import_library_dir, target_soname)
                    LOGGER.debug("Aliasing Wi4MPI fake lib '%s' as guest '%s' at '%s'",
                               fake_lib, target_soname, dest)
                    container.bind_file(fake_lib, dest=dest)


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
                            help="Container image to use",
                            metavar='image')

        parser.add_argument('--files',
                            type=arguments.posix_path_list,
                            help="Files to bind, comma-separated. Supports host:container syntax.",
                            default=[],
                            metavar='files')

        parser.add_argument('--libraries',
                            type=arguments.existing_posix_path_list,
                            help="Libraries to bind, comma-separated",
                            default=[],
                            metavar='libraries')

        parser.add_argument('--source',
                            type=arguments.posix_path,
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

        # Check the environment for the use of Wi4MPI
        wi4mpi_install_dir = wi4mpi_root()

        # List the required libraries for proper Wi4MPI execution
        wi4mpi_required = []
        if wi4mpi_install_dir is not None:
            wi4mpi_required = wi4mpi_libraries(wi4mpi_install_dir)

        # The following is a set of all libraries required. It
        # is used in the container to check version mismatches
        required_libraries = [*args.libraries, *wi4mpi_required]
        
        # NOTE: Do NOT filter OpenMPI core libraries (libmpi.so.40, libopen-pal.so.40, etc.)
        # when Wi4MPI is active - Wi4MPI needs these to translate MPICH->OpenMPI calls.
        # Only the OpenMPI/PMIx plugin FILES should be filtered (see below).
        
        libset = LibrarySet.create_from(required_libraries)
        if libset:
            # Analyze the container to get library information from the environment
            # it offers, using the entrypoint and the above libraries
            container.get_data()

        # Bind all accessible requested files
        files = [p for p in (args.files or []) if Path(p) != Path('/')]
        if len(files) != len(args.files or []):
            LOGGER.warning("Filtered root '/' from bound files to avoid container permission errors.")

        for path in files:
            source, dest = path, None
            if ':' in path:
                parts = path.split(':')
                if len(parts) == 2:
                    source, dest = parts
                else:
                    LOGGER.error("Invalid file binding specification '%s'. Expected 'source:dest'.", path)
                    continue

            if dest is not None:
                if _check_access(source):
                    container.bind_file(source, dest=dest, option=FileOptions.READ_WRITE)
                else:
                    LOGGER.error("File '%s' not found.", source)
            else:
                if _check_access(path):
                    container.bind_file(path, option=FileOptions.READ_WRITE)
                else:
                    LOGGER.error("File '%s' not found.", path)

        # This script is sourced before any other command in the container
        params.source_script_path = args.source

        # Setup the final command and metadata relating to the execution
        params.command = args.cmd
        params.debug = logger.debug_mode()
        params.linker_library_path = generate_rtld_path(
            container, wi4mpi_install_dir)

        # Create a set of libraries to import using a library_set object,
        # then filtering it according to the contents of the container
        final_libset = select_libraries(libset, container, params)

        # Import each library along with all symlinks pointing to it
        for shared_object in final_libset:
            import_library(shared_object, container)

        # MPICH-family aliasing 
        # Skip aliasing when Wi4MPI is active, as it would bypass Wi4MPI translation
        if wi4mpi_install_dir is None:
            alias_guest_mpi_sonames_conservative(final_libset, container)
        else:
            # Wi4MPI is active: create aliases for Wi4MPI fake libraries to match guest SONAMEs
            # This ensures binaries linked to libmpich.so.12 find Wi4MPI's libmpi.so.12
            _alias_wi4mpi_fake_libs_for_guest(wi4mpi_install_dir, container)

        if wi4mpi_install_dir is None:
            # Preload the top-level libraries of the imported set to bypass
            # any potential RPATH settings
            def _path(library: Library):
                return Path(container.import_library_dir,
                            Path(library.binary_path).name).as_posix()

            if config.CONFIGURATION.preload_root_libraries:
                for imported_library_path in map(_path,
                                                 final_libset.top_level):
                    params.preload.append(imported_library_path)
        else:
            # If WI4MPI is found in the environment, import its files and
            # preload its required components
            wi4mpi_import(container, wi4mpi_install_dir)
            params.preload += wi4mpi_preload(wi4mpi_install_dir, container.import_library_dir)
            
            # Override Wi4MPI environment variables to use container paths
            # Wi4MPI uses WI4MPI_RUN_MPI_C_LIB to dlopen the target MPI library
            # The host path won't exist inside the container; we need to use
            # the container path where host libraries are bound
            host_mpi_lib = os.environ.get("WI4MPI_RUN_MPI_C_LIB", "")
            if host_mpi_lib:
                import_library(Library.from_path(Path(host_mpi_lib)), container)
                container_mpi_lib = Path(container.import_library_dir) / Path(host_mpi_lib).name
                params.extra_env["WI4MPI_RUN_MPI_C_LIB"] = container_mpi_lib.as_posix()
                LOGGER.debug("Wi4MPI: Overriding WI4MPI_RUN_MPI_C_LIB to container path: %s", container_mpi_lib)
            
            host_mpi_f_lib = os.environ.get("WI4MPI_RUN_MPI_F_LIB", "")
            if host_mpi_f_lib:
                import_library(Library.from_path(Path(host_mpi_f_lib)), container)
                container_mpi_f_lib = Path(container.import_library_dir) / Path(host_mpi_f_lib).name
                params.extra_env["WI4MPI_RUN_MPI_F_LIB"] = container_mpi_f_lib.as_posix()
                if host_mpi_lib:
                    params.extra_env["WI4MPI_RUN_MPIIO_C_LIB"] = container_mpi_lib.as_posix()
                params.extra_env["WI4MPI_RUN_MPIIO_F_LIB"] = container_mpi_f_lib.as_posix()

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
