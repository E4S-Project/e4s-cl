import pathlib
import os, re
from e4s_cl import EXIT_SUCCESS, E4S_CL_SCRIPT
from e4s_cl.variables import is_master
from e4s_cl.util import which, opened_files, interpret_launcher, create_subprocess_exp
from e4s_cl.error import UniqueAttributeError
from e4s_cl.cli import arguments
from e4s_cl.model.profile import Profile
from e4s_cl.cli.cli_view import AbstractCliView


def separate_files(file_list):
    libraries = []
    files = []

    for file_path in file_list:
        path = pathlib.Path(file_path)
        if path.name == 'ld.so.cache':
            continue

        if re.match(".*\.so.*", path.name):
            libraries.append(file_path)
            continue

        files.append(file_path)

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
            retval, out = create_subprocess_exp(
                launcher + [E4S_CL_SCRIPT, "--slave", "profile", "detect"] +
                program,
                redirect_stdout=True)
            files = list(filter(None, set(out.split('\n'))))
        else:
            # No launcher, analyse the command
            files = opened_files(args.cmd)

        # There are two cases: this is a master process, in which case the output
        # must be processed, or this is a slave process, where we just print it all on stdout
        # in a format the master will understand
        if not is_master():
            print("\n".join(files))
            return

        files = list(filter(None, files))
        libs, files = separate_files(files)
        print("\n".join(["Libraries:"] + libs))
        print("\n".join(["Files:"] + files))

        if args.output:
            data = {'name': args.output, 'libraries': libs, 'files': files}
            try:
                Profile.controller().create(data)
            except UniqueAttributeError:
                self.parser.error("A profile named '%s' already exists." %
                                  args.output)

        return EXIT_SUCCESS


COMMAND = ProfileDetectCommand(Profile, __name__)
