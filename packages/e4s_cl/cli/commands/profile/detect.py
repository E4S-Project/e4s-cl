"""
The **profile detect** command will create a profile from the analysis of a \
MPI binary's execution. This process uses system call interception to produce \
an exhaustive list of files required by the MPI process.

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

import re
from json import JSONDecodeError
from pathlib import Path
from typing import List

from e4s_cl import EXIT_SUCCESS, EXIT_FAILURE, E4S_CL_SCRIPT, logger
from e4s_cl.variables import is_master
from e4s_cl.util import opened_files, create_subprocess_exp, flatten, json_dumps, json_loads
from e4s_cl.cf.libraries import is_elf, resolve
from e4s_cl.cf.launchers import interpret
from e4s_cl.cli import arguments
from e4s_cl.model.profile import Profile
from e4s_cl.cli.cli_view import AbstractCliView

LOGGER = logger.get_logger(__name__)


def filter_files(path_list: List[Path]):
    """
    Categorize paths into libraries or files

    Libraries are resolved with the linker and are to be imported in a special
    location. They can only be ELF files.

    Files are referenced using their paths and have to be imported at the same
    location. They can be ELF objects that are dynamically loaded by the library.
    """
    libraries, files = set(), set()

    for path in path_list:
        try:
            if not path.exists() or path.is_dir():
                continue
        except PermissionError:
            continue

        # Process shared objects
        if is_elf(path):
            if resolve(path.name):
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
            if not filtered and re.match("^%s.*" % expr, path.as_posix()):
                filtered = True
                break

        if not filtered:
            files.add(path.as_posix())
            LOGGER.debug("File %s is a regular file (non-blacklisted)",
                         path.name)

    return libraries, files


class ProfileDetectCommand(AbstractCliView):
    """``profile create`` subcommand."""
    def _construct_parser(self):
        usage = "%s [-p profile] <mpi_launcher command>" % self.command
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

    def main(self, argv):
        args = self._parse_args(argv)

        if not args.cmd:
            return EXIT_FAILURE

        launcher, program = interpret(args.cmd)

        if launcher:
            # If a launcher is present, act as a launcher
            returncode, json_data = create_subprocess_exp(
                launcher + [E4S_CL_SCRIPT, "--slave", "profile", "detect"] +
                program + ["4"],
                redirect_stdout=True)

            if not returncode:
                file_paths, library_paths = [], []

                for line in json_data.split('\n'):
                    try:
                        data = json_loads(line)
                        file_paths.append(data['files'])
                        library_paths.append(data['libraries'])
                    except JSONDecodeError:
                        pass

                files = list(set(flatten(file_paths)))
                libs = list(set(flatten(library_paths)))

        else:
            # No launcher, analyse the command
            returncode, accessed_files = opened_files(args.cmd)
            libs, files = filter_files(accessed_files)

        if returncode:
            if is_master():
                LOGGER.error("Failed to determine necessary libraries.")
            return EXIT_FAILURE

        # There are two cases: this is a master process, in which case the output
        # must be processed, or this is a slave process, where we just print it
        # all on stdout in a format the master process will understand
        if not is_master():
            print(json_dumps({
                'files': files,
                'libraries': libs,
            }))
            return EXIT_SUCCESS

        # Save the resuling list to a profile
        controller = Profile.controller()
        if args.profile_name:
            identifier = {'name': args.profile_name}
            profile = controller.one(identifier)

            if not profile:
                try:
                    profile = controller.create(identifier)
                except Exception as err:  #TODO check what errors can be handled here
                    LOGGER.debug(str(err))
                    LOGGER.error("Profile creation failed.")
                    return EXIT_FAILURE
        else:
            profile = controller.selected()

            if not profile:
                LOGGER.error(
                    "No output profile selected or given as an argument.")
                return EXIT_FAILURE

            identifier = {'name': profile.get('name')}

        data = {'libraries': libs, 'files': files}
        try:
            controller.update(data, identifier)
        except Exception as err:  # TODO same as above
            LOGGER.debug(str(err))
            LOGGER.error("Profile update failed.")
            return EXIT_FAILURE

        return EXIT_SUCCESS


COMMAND = ProfileDetectCommand(Profile, __name__)
