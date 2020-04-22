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

HOST_LIBS_DIR = Path('/hostlibs/').as_posix()

def _existing_backend(string):
    if not string in containers.BACKENDS:
        raise ArgumentTypeError("Backend {} is not available on this machine".format(string))

    return string

def _argument_path(string):
    path = Path(string)

    if not path.exists():
        raise ArgumentTypeError("File {} does not exist".format(path.as_posix()))

    return path

def _argument_path_comma_list(string):
    return [_argument_path(data) for data in string.split(',')]

def compute_libs(lib_list, container):
    output = container.run(['ldconfig', '-p'], redirect_stdout=True)
    present_in_container = [line.strip().split(' ')[0] for line in output.split('\n')[1:]]
    selected = {}

    for path in lib_list:
        dependencies = list_dependencies(path)
        for dependency in dependencies.keys():
            if dependency not in present_in_container and dependencies[dependency]['path']:
                selected.update({dependency: dependencies[dependency]['path']})

    for path in selected.values():
        container.bind_file(path, dest="{}/{}".format(HOST_LIBS_DIR, Path(path).name), options='ro')

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

        parser.add_argument("--backend",
                            choices=containers.BACKENDS,
                            type=_existing_backend,
                            dest='backend',
                            required=True,
                            help="Specify the container backend",
                            metavar='Available')

        parser.add_argument('--image',
                            type=_argument_path,
                            required=True,
                            help="Container image to use",
                            metavar='image')

        parser.add_argument('--files',
                            type=_argument_path_comma_list,
                            help="Files to bind, comma-separated",
                            metavar='files')

        parser.add_argument('--libraries',
                            type=_argument_path_comma_list,
                            help="Libraries to bind, comma-separated",
                            metavar='libraries')

        parser.add_argument('cmd',
                            type=str,
                            help="Executable command, e.g. './a.out'",
                            metavar='command',
                            nargs=arguments.REMAINDER)

        """Simpler way of specifying backend, but less robust catching errors
        if containers.BACKENDS:
            group = parser.add_mutually_exclusive_group(required=True)
            for backend in containers.BACKENDS:
                group.add_argument("--{}".format(backend),
                        help="Use {} as the container backend".format(backend),
                        dest='backend',
                        action='store_const',
                        const=backend)"""

        return parser

    def main(self, argv):
        args = self._parse_args(argv)
        container = containers.Container(backend=args.backend, image=args.image)

        if args.libraries:
            compute_libs(args.libraries, container)
            #container.bind_env_var('LD_DEBUG', 'files')
            container.bind_env_var('LD_LIBRARY_PATH', HOST_LIBS_DIR)

        if args.files:
            for path in args.files:
                container.bind_file(path, dest=path, options='ro')

        container.run(args.cmd, redirect_stdout=False)

        return EXIT_SUCCESS
    
COMMAND = ExecuteCommand(__name__, summary_fmt="Execute a command in a container with a tailor-made environment.")
