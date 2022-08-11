"""
The **profile detect** command will create a profile from the analysis of \
the inputted MPI binary's execution. This process uses system call \
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

Use :code:`-p/--profile` to select a output profile. If the option is not \
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
                         path_contains, apply_filters)
from e4s_cl.cf.trace import opened_files
from e4s_cl.cf.launchers import interpret, get_reserved_directories
from e4s_cl.cli import arguments
from e4s_cl.model.profile import Profile
from e4s_cl.cli.cli_view import AbstractCliView

LOGGER = logger.get_logger(__name__)

LAUNCHER_VAR = '__E4S_CL_DETECT_LAUNCHER'


def _same_file(lhs: Any, rhs: Any) -> bool:
    """Assert two files are the same file, even through symbolic links"""

    def _force_cast(val: Any) -> bool:
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
    libraries, files = set(), set()
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
    regul_files = valid_files - elf_objects

    library_set = LibrarySet.create_from(elf_objects)

    def _resolved(path: Path) -> bool:
        library = Library.from_path(path)
        resolved_path = resolve(library.soname,
                                rpath=orig_rpath + library_set.rpath,
                                runpath=orig_runpath + library_set.runpath)

        return _same_file(path, resolved_path)

    libraries = set(filter(_resolved, elf_objects))
    orphan_libraries = elf_objects - libraries

    filtered_files = set(
        apply_filters([_not_cache, _not_blacklisted, _waived_launcher],
                      regul_files))
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
                profile = controller.create(identifier)
            except Exception as err:  #TODO check what errors can arise
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
        return parser

    def detect_subprocesses(self, launcher, program):
        """
        Run process profiling in subprocesses with the detected launcher
        """
        files, libs = [], []

        with variables.ParentStatus():
            os.environ[LAUNCHER_VAR] = launcher[0]
            # If a launcher is present, act as a launcher
            returncode, json_data = run_e4scl_subprocess([
                *launcher, sys.executable, E4S_CL_SCRIPT, "profile", "detect",
                *program
            ],
                                                         capture_output=True)

        if returncode:
            LOGGER.error(
                "Failed to determine necessary libraries: program exited with code %d",
                returncode)
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

    def main(self, argv):
        args = self._parse_args(argv)

        if not args.cmd:
            return EXIT_FAILURE

        launcher, program = interpret(args.cmd)

        libs, files = [], []
        if launcher:
            libs, files = self.detect_subprocesses(launcher, program)
        else:
            launcher = os.environ.get(LAUNCHER_VAR, '').split(' ')

            # No launcher, analyse the command
            returncode, accessed_files = opened_files(args.cmd)

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
