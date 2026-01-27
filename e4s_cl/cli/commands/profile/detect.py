"""
The **profile detect** command will create a profile from the analysis of \
the given MPI command's execution. This process uses system call \
monitoring to produce an exhaustive list of files and libraries required \
by the MPI installation.

.. warning::
    To get a complete dependency detection, it is best to ensure the following:

    * The MPI launcher and binary should use the host's MPI library, to be \
imported in the future containers;
    * The MPI program should call at least one collective to ensure the use \
of the network stack;
    * The process should be run on multiple nodes using the target network. \
Failure to do so may result in erroneous detection of communication libraries \
and thus may create communication errors when using the profile.

Use :code:`-p/--profile` to select an output profile. If the option is not \
present, the selected profile will be overwritten instead.

.. warning::
   Not specifying a profile will overwrite the selected profile on success !

Examples
----------

.. code::

    mpicc -o ping-pong ping-pong.c
    e4s-cl profile detect -p profile-detected \\
            mpirun -np 2 -ppn 1 -hosts node1,node2 ./ping-pong

"""

import os
import sys
from json import JSONDecodeError
from pathlib import Path
from typing import List, Optional, Any

from sotools import is_elf
from sotools.linker import resolve
from sotools.libraryset import Library, LibrarySet

from e4s_cl import (EXIT_SUCCESS, EXIT_FAILURE, E4S_CL_SCRIPT, logger,
                    INIT_TEMP_PROFILE_NAME)

from e4s_cl import variables
from e4s_cl.error import ProfileSelectionError
from e4s_cl.util import (run_e4scl_subprocess, flatten, json_dumps, json_loads,
                         path_contains, apply_filters, which)
from e4s_cl.cf.trace import opened_files
from e4s_cl.cf.launchers import interpret, get_reserved_directories
from e4s_cl.cli import arguments
from e4s_cl.model.profile import Profile
from e4s_cl.cli.cli_view import AbstractCliView

LOGGER = logger.get_logger(__name__)

LAUNCHER_VAR = '__E4S_CL_DETECT_LAUNCHER'


def _same_file(lhs: Any, rhs: Any) -> bool:
    """Assert two files are the same file, even through symbolic links"""

    def _force_cast(val: Any) -> Path:
        allowed = [str, bytes, os.PathLike]
        for check in allowed:
            if isinstance(val, check):
                return Path(val)
        return Path()

    return _force_cast(lhs).resolve() == _force_cast(rhs).resolve()


def filter_files(path_list: List[Path],
                 launcher: List[str] = None,
                 original_binary: Optional[Library] = None):
    """
    Categorize paths into libraries or files

    Libraries are resolved with the linker and are to be imported in a special
    location. They can only be ELF files.

    Files are referenced using their paths and have to be imported at the same
    location. They can be ELF objects that are dynamically loaded by the library.
    """
    orig_rpath, orig_runpath = [], []

    if original_binary is not None:
        orig_rpath = original_binary.rpath
        orig_runpath = original_binary.runpath

    launcher_reserved_paths = get_reserved_directories(launcher)

    def _not_cache(path: Path) -> bool:
        return path != Path('/etc/ld.so.cache')

    def _not_blacklisted(path: Path) -> bool:
        blacklist = map(Path, ["/tmp", "/sys", "/proc", "/dev", "/run"])
        for entry in blacklist:
            if path_contains(entry, path):
                return False
        return True

    def _not_root(path: Path) -> bool:
        return path != Path('/')

    def _existence(path: Path) -> bool:
        """Assert the file still exists and is accessible"""
        try:
            if not path.exists() or path.is_dir():
                return False
        except PermissionError:
            return False
        return True

    def _waived_launcher(path: Path) -> bool:
        """Assert the file path does not correspond to a directory used by the launcher"""
        for launcher_path in launcher_reserved_paths:
            if path_contains(launcher_path, path):
                return False
        return True

    valid_files = set(filter(_existence, path_list))
    elf_objects = set(filter(is_elf, valid_files))
    regular_files = valid_files - elf_objects

    library_set = LibrarySet.create_from(elf_objects)
    if original_binary:
        library_set.add(original_binary)

    def _resolved(path: Path) -> bool:
        """Assert the given path (assuming it to be an elf object) corresponds
        to a library that is resolved via the linker and present in the dynamic
        dependencies of the set.

        This allows us to filter out libraries that are loaded randomly from
        the process from the ones loaded using the standard linux run-time
        linker system. 

        This influences the import method of the objects, as we can control the
        linker system using LD_LIBRARY_PATH, but manually loaded libraries are
        expected to be found at a hardcoded path, and need to be present in
        a container at the same path."""
        # Extract a soname from the given path
        library = Library.from_path(path)

        # Try resolving this soname using the linking rules
        resolved_soname = resolve(library.soname,
                                  rpath=orig_rpath + library_set.rpath,
                                  runpath=orig_runpath + library_set.runpath)

        # For some libraries that disregard SONAME rules (CRAY), try resolving
        # using the file name as it is the one that is actually relevant
        resolved_filename = resolve(path.name,
                                    rpath=orig_rpath + library_set.rpath,
                                    runpath=orig_runpath + library_set.runpath)

        return (_same_file(path, resolved_soname)
                or _same_file(path, resolved_filename)
                or library not in library_set.top_level)

    libraries = set(filter(_resolved, elf_objects))
    orphan_libraries = elf_objects - libraries

    filtered_files = set(
        apply_filters([_not_cache, _not_blacklisted, _not_root, _waived_launcher],
                      regular_files))
    files = filtered_files.union(orphan_libraries)

    return set(map(str, libraries)), set(map(str, files))


def save_to_profile(profile_name, libraries, files) -> int:
    """
    Save the libraries and files to a profile with the name profile_name
    """
    controller = Profile.controller()
    if profile_name:
        identifier = {'name': profile_name}
        profile = controller.one(identifier)

        if not profile:
            try:
                controller.create(identifier)
            except Exception as err:  # TODO check what errors can arise
                LOGGER.error("Profile creation failed: %s", str(err))
                return EXIT_FAILURE
    else:
        try:
            profile = controller.selected()
        except ProfileSelectionError:
            LOGGER.error("No output profile selected or given as an argument.")
            return EXIT_FAILURE

        if profile.get('name') != INIT_TEMP_PROFILE_NAME:
            LOGGER.warning(
                "No profile specified: currently selected profile will be updated."
            )

        identifier = {'name': profile.get('name')}

    data = {'libraries': list(libraries), 'files': list(files)}
    try:
        controller.update(data, identifier)
    except Exception as err:  # TODO same as above
        LOGGER.error("Profile update failed: %s", str(err))
        return EXIT_FAILURE

    return EXIT_SUCCESS


CORE_MPI_PREFIXES = (
    'libmpi',
    'libmpich',
    'libopen-rte',
    'liborte',
    'liboshmem',
)


def _filter_mpi_artifacts(libs: List[Path], files: List[Path],
                          launcher: Path,
                          mpi_filter: str = 'auto',
                          exclude_prefixes: List[str] = None,
                          exclude_names: List[str] = None) -> (List[str], List[str]):
    """
    Filter MPI-related artifacts using one of three modes:
      - off: no filtering (trust ptrace)
      - manual: apply user exclusions only
      - auto: infer authoritative MPI from libmpi and launcher prefix

    Manual exclusions are always applied before MPI filtering.
    Filtering fails open on ambiguity.
    """
    if not libs or not launcher:
        return [str(p) for p in libs], [str(p) for p in files]

    if mpi_filter == 'off':
        return [str(p) for p in libs], [str(p) for p in files]

    exclude_prefixes = exclude_prefixes or []
    exclude_names = exclude_names or []

    # Normalize exclude prefixes
    normalized_exclude_prefixes = [Path(p).resolve() for p in exclude_prefixes]

    # Warn if exclusions are used in auto mode
    if mpi_filter == 'auto' and (exclude_prefixes or exclude_names):
        LOGGER.warning(
            "Manual exclusions are applied before MPI auto-filtering. "
            "Consider --mpi-filter=manual if this is intentional."
        )

    # Handle manual exclusions first, regardless of auto/manual mode
    if normalized_exclude_prefixes or exclude_names:
        kept_libs = []
        for lib in libs:
            resolved = lib.resolve()
            excluded = False
            if resolved.name in exclude_names:
                excluded = True

            if not excluded:
                for prefix in normalized_exclude_prefixes:
                    if path_contains(prefix, resolved):
                        excluded = True
                        break

            if excluded:
                LOGGER.info("Excluding user-blacklisted artifact %s", lib)
                continue
            kept_libs.append(lib)
        libs = kept_libs

    if mpi_filter == 'manual':
        return [str(p) for p in libs], [str(p) for p in files]

    resolved_launcher = launcher
    if not launcher.is_absolute():
        path_str = which(str(launcher))
        if path_str:
            resolved_launcher = Path(path_str)

    launcher = resolved_launcher.resolve()

    def _get_lib_prefix(path: Path) -> Path:
        for marker in ['lib', 'lib64']:
            if marker in path.parts:
                return Path(*path.parts[:path.parts.index(marker)])
        return path.parent

    def _is_core_mpi(path: Path) -> bool:
        name = path.name
        return any(name.startswith(prefix) for prefix in CORE_MPI_PREFIXES)

    resolved_libs = [lib.resolve() for lib in libs]

    # 1. Identify authoritative libmpi candidates
    candidates = list(set([
        lib for lib in resolved_libs
        if lib.name == 'libmpi.so' or lib.name.startswith('libmpi.so.')
    ]))

    if not candidates:
        return [str(p) for p in libs], [str(p) for p in files]

    # Check for system launcher
    is_system_launcher = str(launcher).startswith('/usr/bin') or str(launcher).startswith('/bin')

    selected_lib = None

    if is_system_launcher:
        if len(candidates) == 1:
            selected_lib = candidates[0]
        else:
             # Ambiguity or 0 -> fail open
             return [str(p) for p in libs], [str(p) for p in files]
    else:
        # Standard launcher
        if len(candidates) == 1:
            selected_lib = candidates[0]
        else:
            # Multiple candidates. Filter by overlap with launcher prefix.
            launcher_prefix = launcher.parent
            if 'bin' in launcher.parts:
                 launcher_prefix = Path(*launcher.parts[:launcher.parts.index('bin')])

            matches = []
            for cand in candidates:
                 cand_prefix = _get_lib_prefix(cand)
                 # Check overlap
                 if (launcher_prefix == cand_prefix or
                     launcher_prefix in cand_prefix.parents or
                     cand_prefix in launcher_prefix.parents):
                     matches.append(cand)

            if len(matches) == 1:
                selected_lib = matches[0]
            else:
                 # No match or Multiple matches -> Fail open
                 return [str(p) for p in libs], [str(p) for p in files]

    # We have a selected authoritative library
    selected_prefix = _get_lib_prefix(selected_lib)

    LOGGER.info("MPI filtering mode: %s", mpi_filter)
    LOGGER.info("Authoritative MPI: %s", selected_lib)

    kept_libs = []
    discarded_libs = []

    for lib in libs:
        resolved = lib.resolve()

        # Keep non-core libraries always (whitelist)
        if not _is_core_mpi(resolved):
            kept_libs.append(lib)
            continue

        # For core libs, check prefix consistency with authoritative lib
        lib_prefix = _get_lib_prefix(resolved)

        if (selected_prefix == lib_prefix or
            selected_prefix in lib_prefix.parents or
            lib_prefix in selected_prefix.parents):
             kept_libs.append(lib)
        else:
             LOGGER.info("Discarding MPI artifact %s (prefix mismatch with %s)", lib, selected_lib)
             discarded_libs.append(lib)

    if discarded_libs:
        LOGGER.info("Discarded core MPI libs: %s", [l.name for l in discarded_libs])

    return [str(p) for p in kept_libs], [str(p) for p in files]


def detect_subprocesses(launcher, program):
    """Run process profiling in subprocesses with the detected launcher"""
    files, libs = [], []

    os.environ[LAUNCHER_VAR] = launcher[0]
    # If a launcher is present, act as a launcher
    # Use a timeout to prevent hanging on mpirun with multiple processes
    return_code, json_data = run_e4scl_subprocess([
        *launcher, sys.executable, E4S_CL_SCRIPT, "profile", "detect", *program
    ],
                                                  capture_output=True,
                                                  timeout=60)

    if return_code:
        LOGGER.error(
            "Failed to determine necessary libraries: program exited with code %d",
            return_code)
        return libs, files

    # Merge all the data sent back into files and libraries
    file_paths, library_paths = [], []

    for line in json_data.split('\n'):
        try:
            data = json_loads(line)
            file_paths.append(data['files'])
            library_paths.append(data['libraries'])
        except (JSONDecodeError, TypeError):
            pass

    files = list(set(flatten(file_paths)))
    libs = list(set(flatten(library_paths)))

    return libs, files


class ProfileDetectCommand(AbstractCliView):
    """``profile create`` subcommand."""

    def _construct_parser(self):
        usage = f"{self.command} [-p profile] <mpi_launcher command>"
        parser = arguments.get_parser(prog=self.command,
                                      usage=usage,
                                      description=self.summary)

        parser.add_argument('-p',
                            '--profile',
                            help="Output profile",
                            dest='profile_name',
                            metavar='profile_name')

        parser.add_argument('cmd',
                            help="Executable command, e.g. './a.out'",
                            metavar='command',
                            nargs=arguments.REMAINDER)
        
        parser.add_argument('--mpi-filter',
                            help="Filter mode for MPI artifacts (default: auto)",
                            choices=['auto', 'off', 'manual'],
                            default='auto')
        
        parser.add_argument('--exclude-lib-prefix',
                            help="Exclude libraries under this prefix when --mpi-filter=manual",
                            action='append',
                            default=[])

        parser.add_argument('--exclude-lib-name',
                            help="Exclude libraries with this exact name when --mpi-filter=manual",
                            action='append',
                            default=[])

        return parser

    def main(self, argv):
        args = self._parse_args(argv)

        if not args.cmd:
            return EXIT_FAILURE

        launcher, program = interpret(args.cmd)

        if launcher:
            libs, files = detect_subprocesses(launcher, program)

            # Filter out artifacts from other MPI implementations
            libs, files = _filter_mpi_artifacts([Path(l) for l in libs],
                                                [Path(f) for f in files],
                                                Path(launcher[0]),
                                                mpi_filter=getattr(args, 'mpi_filter', 'auto'),
                                                exclude_prefixes=getattr(args, 'exclude_lib_prefix', []),
                                                exclude_names=getattr(args, 'exclude_lib_name', [])
                                                )
        else:
            launcher = os.environ.get(LAUNCHER_VAR, '').split(' ')

            # No launcher, analyse the command
            return_code, accessed_files = opened_files(args.cmd)

            if return_code:
                LOGGER.warning("Command %s failed with error code %d",
                               args.cmd, return_code)

            # Access the binary to check ELF metadata
            binary = None
            if is_elf(args.cmd[0]):
                binary = Library.from_path(args.cmd[0])

            libs, files = filter_files(accessed_files,
                                       launcher,
                                       original_binary=binary)
            LOGGER.debug("Accessed files: %s, %s", libs, files)

        # There are two cases: this is a parent process, in which case we
        # interpret the output of children, or this is a child process, where
        # we just print data on stdout
        if not variables.is_parent():
            print(json_dumps({
                'files': files,
                'libraries': libs,
            }))
            return EXIT_SUCCESS

        return save_to_profile(args.profile_name, libs, files)


COMMAND = ProfileDetectCommand(Profile, __name__)
