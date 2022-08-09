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
from typing import List

from e4s_cl import (EXIT_SUCCESS, EXIT_FAILURE, E4S_CL_SCRIPT, logger,
                    INIT_TEMP_PROFILE_NAME)

from e4s_cl import variables
from e4s_cl.error import ProfileSelectionError
from e4s_cl.util import (run_e4scl_subprocess, flatten, json_dumps, json_loads,
                         path_contains)
from e4s_cl.cf.trace import opened_files
from e4s_cl.cf.libraries import is_elf, resolve, Library
from e4s_cl.cf.launchers import interpret, get_reserved_directories
from e4s_cl.cli import arguments
from e4s_cl.model.profile import Profile
from e4s_cl.cli.cli_view import AbstractCliView

LOGGER = logger.get_logger(__name__)

LAUNCHER_VAR = '__E4S_CL_DETECT_LAUNCHER'


def filter_files(path_list: List[Path], launcher: List[str] = None):
    """
    Categorize paths into libraries or files

    Libraries are resolved with the linker and are to be imported in a special
    location. They can only be ELF files.

    Files are referenced using their paths and have to be imported at the same
    location. They can be ELF objects that are dynamically loaded by the library.
    """
    libraries, files = set(), set()

    launcher_reserved_paths = get_reserved_directories(launcher)

    for path in path_list:
        try:
            if not path.exists() or path.is_dir():
                continue
        except PermissionError:
            continue

        waived_launcher = False
        for launcher_path in launcher_reserved_paths:
            if path_contains(launcher_path, path):
                files.add(str(launcher_path))
                waived_launcher = True
                break

        if waived_launcher:
            continue

        # Process shared objects
        if is_elf(path):
            library = Library.from_path(path)
            resolved_path = resolve(library.soname)

            if resolved_path and Path(path).resolve() == Path(
                    resolved_path).resolve():
                # The library is resolved by the linker, treat it as a library
                libraries.add(path.as_posix())
                LOGGER.debug("File %s is a library", path.name)

            else:
                # It is a library BUT must be imported with a full path
                files.add(path.as_posix())
                LOGGER.debug("File %s is a library (non-standard)", path.name)

            continue

        # Discard the linker cache, opened by default for every binary
        if path.name == 'ld.so.cache':
            continue

        # Process files
        blacklist = ["/tmp", "/sys", "/proc", "/dev", "/run"]
        filtered = False
        for expr in blacklist:
            if not filtered and path.as_posix().startswith(expr):
                filtered = True
                break

        if not filtered:
            files.add(path.as_posix())
            LOGGER.debug("File %s is a regular file (non-blacklisted)",
                         path.name)

    return libraries, files


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
            libs, files = filter_files(accessed_files, launcher)
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
