"""
Launch an executable and catch syscalls to determine a list of files. Output it to a profile if asked to.
"""

import json
import pathlib
import os
import re
from e4s_cl import EXIT_SUCCESS, EXIT_FAILURE, E4S_CL_SCRIPT, logger
from e4s_cl.variables import is_master
from e4s_cl.util import which, opened_files, create_subprocess_exp, flatten
from e4s_cl.cf.libraries import host_libraries, ldd
from e4s_cl.cf.launchers import interpret
from e4s_cl.error import UniqueAttributeError
from e4s_cl.cli import arguments
from e4s_cl.model.profile import Profile
from e4s_cl.cli.cli_view import AbstractCliView

LOGGER = logger.get_logger(__name__)


def filter_files(path_list, ldd_requirements):
    """
    Filter a list of files from syscalls into categories
    """
    libraries, paths = [], []

    # As in `man ld.so`
    linker_default_paths = [
        pathlib.Path('/lib'),
        pathlib.Path('/lib64'),
        pathlib.Path('/usr/lib'),
        pathlib.Path('/usr/lib64')
    ]

    # Cut a:b:c in a Path list if set
    linker_env_paths = [
        pathlib.Path(dir)
        for dir in filter(lambda x: x,
                          os.environ.get('LD_LIBRARY_PATH', '').split(':'))
    ]

    for path in path_list:
        if not path.exists() or path.is_dir():
            continue

        # Discard the linker cache
        if path.name == 'ld.so.cache':
            continue

        # Process shared objects
        if re.match(r".*\.so.*", path.name):
            if path.name in host_libraries().keys():
                # The library is in the cache, it can be found using a soname
                libraries.append(path.as_posix())
                LOGGER.debug("File %s is a library (cache)", path.name)
            elif path.name in ldd_requirements.keys() \
                and ldd_requirements[path.name].get('found'):
                # The library is not in the cache, but still found by the linker
                libraries.append(path.as_posix())
                LOGGER.debug("File %s is a library (found)", path.name)
            elif path.parent in linker_default_paths + linker_env_paths:
                # If not in the cache, but still found by the linker
                libraries.append(path.as_posix())
                LOGGER.debug("File %s is a library (default)", path.name)
            else:
                # Not standard, it is a library BUT must be imported with a full path
                paths.append(path.as_posix())
                LOGGER.debug("File %s is a library (non-standard)", path.name)
            continue

        # Process files
        blacklist = ["/tmp", "/sys", "/proc", "/dev", "/run"]
        filtered = False
        for expr in blacklist:
            if not filtered and re.match("^%s.*" % expr, path.as_posix()):
                filtered = True

        if not filtered:
            paths.append(path.as_posix())
            LOGGER.debug("File %s is a regular file (non-blacklisted)",
                         path.name)

    return libraries, paths


class ProfileDetectCommand(AbstractCliView):
    """``profile create`` subcommand."""
    def _construct_parser(self):
        usage = "%s" % self.command
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
        ldd_requirements = {}

        if launcher:
            # If a launcher is present, create subprocesses and aggregate the results
            returncode, json_data = create_subprocess_exp(
                launcher + [E4S_CL_SCRIPT, "--slave", "profile", "detect"] +
                program,
                redirect_stdout=True)

            if not returncode:
                file_paths, library_paths = [], []

                for line in json_data.split('\n'):
                    try:
                        data = json.loads(line)
                        file_paths.append(data['files'])
                        library_paths.append(data['libraries'])
                    except json.JSONDecodeError:
                        pass

                files = list(set(flatten(file_paths)))
                libs = list(set(flatten(library_paths)))

        else:
            # No launcher, analyse the command
            returncode, accessed_files = opened_files(args.cmd)
            base_command = which(args.cmd[0])
            if base_command:
                ldd_requirements = ldd(base_command)
            libs, files = filter_files(accessed_files, ldd_requirements)

        if returncode:
            if is_master():
                LOGGER.error("Failed to determine necessary libraries.")
            return EXIT_FAILURE

        # There are two cases: this is a master process, in which case the output
        # must be processed, or this is a slave process, where we just print it all on stdout
        # in a format the master will understand
        if not is_master():
            print(json.dumps({
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
                except Exception as e:  #TODO check what errors can be handled here
                    LOGGER.debug(str(e))
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
        except Exception as e:  # TODO same as above
            LOGGER.debug(str(e))
            LOGGER.error("Profile update failed.")
            return EXIT_FAILURE

        return EXIT_SUCCESS


COMMAND = ProfileDetectCommand(Profile, __name__)
