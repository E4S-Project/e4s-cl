import json
import pathlib
import os, re
from e4s_cl import EXIT_SUCCESS, EXIT_FAILURE, E4S_CL_SCRIPT, logger
from e4s_cl.variables import is_master
from e4s_cl.util import which, opened_files, interpret_launcher, create_subprocess_exp
from e4s_cl.error import UniqueAttributeError
from e4s_cl.cli import arguments
from e4s_cl.model.profile import Profile
from e4s_cl.cli.cli_view import AbstractCliView

LOGGER = logger.get_logger(__name__)


def separate_files(file_list):
    libraries = []
    files = []

    for path in file_list:
        if path.name == 'ld.so.cache':
            continue

        if re.match(".*\.so.*", path.name):
            libraries.append(path)
            continue

        files.append(path)

    return libraries, files


class ProfileDetectCommand(AbstractCliView):
    """``profile create`` subcommand."""
    def _construct_parser(self):
        usage = "%s" % self.command
        parser = arguments.get_parser(prog=self.command,
                                      usage=usage,
                                      description=self.summary)

        parser.add_argument('-o',
                            '--output',
                            help="Output profile",
                            metavar='output')

        parser.add_argument('cmd',
                            help="Executable command, e.g. './a.out'",
                            metavar='command',
                            nargs=arguments.REMAINDER)
        return parser

    def main(self, argv):
        args = self._parse_args(argv)

        if not args.cmd:
            return

        launcher, program = interpret_launcher(args.cmd)

        if launcher:
            # If a launcher is present, create subprocesses and aggregate the results
            returncode, json_data = create_subprocess_exp(
                launcher + [E4S_CL_SCRIPT, "--slave", "profile", "detect"] +
                program,
                redirect_stdout=True)
            if not returncode:
                files = [pathlib.Path(path) for path in json.loads(json_data)]
        else:
            # No launcher, analyse the command
            returncode, files = opened_files(args.cmd)

        if returncode:
            if is_master():
                LOGGER.error("Failed to determine necessary libraries.")
            return EXIT_FAILURE

        # There are two cases: this is a master process, in which case the output
        # must be processed, or this is a slave process, where we just print it all on stdout
        # in a format the master will understand
        if not is_master():
            print(json.dumps([path.as_posix() for path in files]))
            return

        libs, files = separate_files(files)
        print("\n".join(["Libraries:"] + [lib.name for lib in libs]))
        print("\n".join(["Files:"] + [f.as_posix() for f in files]))

        if args.output:
            data = {'name': args.output, 'libraries': libs, 'files': files}
            try:
                Profile.controller().create(data)
            except UniqueAttributeError:
                self.parser.error("A profile named '%s' already exists." %
                                  args.output)

        return EXIT_SUCCESS


COMMAND = ProfileDetectCommand(Profile, __name__)
