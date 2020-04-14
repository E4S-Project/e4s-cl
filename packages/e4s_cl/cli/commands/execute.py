import os
from pathlib import Path
from e4s_cl import EXIT_SUCCESS, HELP_CONTACT, E4S_CL_SCRIPT
from e4s_cl import logger, cli
from e4s_cl.util import list_dependencies
from e4s_cl.cli import arguments
from e4s_cl.cli.command import AbstractCommand
from argparse import ArgumentTypeError
from e4s_cl.cf import containers

LOGGER = logger.get_logger(__name__)
_SCRIPT_CMD = os.path.basename(E4S_CL_SCRIPT)

def _comma_list(string):
    items = [Path(data) for data in string.split(',')]

    def assertExistence(path):
        if not path.exists():
            raise ArgumentTypeError("File {} does not exist".format(path.as_posix()))

    [assertExistence(item) for item in items]

    return items

class ExecuteCommand(AbstractCommand):
    """``help`` subcommand."""

    @classmethod
    def _parse_dependencies(cls, libraries):
        deps = {}

        for path in libraries:
            deps.update(list_dependencies(path))

        return deps

    def _construct_parser(self):
        usage = "%s [arguments] <command> [command_arguments]" % self.command
        parser = arguments.get_parser(prog=self.command, usage=usage, description=self.summary)
        parser.add_argument('--image',
                            help="Container image to use",
                            #type= TODO Container iamge checking method
                            metavar='image')
        parser.add_argument('--files',
                            help="Files to bind, comma-separated",
                            metavar='files',
                            type=str,
                            nargs=1)
        parser.add_argument('--libraries',
                            help="Libraries to bind, comma-separated",
                            metavar='libraries',
                            type=_comma_list)
        parser.add_argument('cmd',
                            help="Executable command, e.g. './a.out'",
                            metavar='command',
                            type=str,
                            nargs=arguments.REMAINDER)

        if containers.BACKENDS:
            group = parser.add_mutually_exclusive_group(required=True)
            for backend in containers.BACKENDS:
                group.add_argument("--{}".format(backend),
                        help="Use {} as the container backend".format(backend),
                        action='store_true')

        return parser

    def main(self, argv):
        args = self._parse_args(argv)
        #deps = ExecuteCommand._parse_dependencies(args.libraries)
        container = containers.Container(backend='singularity', image=args.image)
        #container.bind_file('/etc/test')
        container.run(" ".join(args.cmd))
        return EXIT_SUCCESS
    
COMMAND = ExecuteCommand(__name__, summary_fmt="Execute a command in a container with a tailor-made environment.")
