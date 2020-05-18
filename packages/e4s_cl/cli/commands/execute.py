"""Execute command

Definition of arguments and hooks related to the execute command,
file import calculations, and execution of a program passed as an
argument.
"""

import os
from pathlib import Path
from argparse import ArgumentTypeError
from e4s_cl import EXIT_SUCCESS, E4S_CL_SCRIPT
from e4s_cl import logger, util, variables
from e4s_cl.cli import arguments
from e4s_cl.cli.command import AbstractCommand
from e4s_cl.cf import containers

LOGGER = logger.get_logger(__name__)
_SCRIPT_CMD = os.path.basename(E4S_CL_SCRIPT)

HOST_LIBS_DIR = Path('/hostlibs/').as_posix()


def _existing_backend(string):
    """Argument type callback.
    Asserts that the selected backend is available."""
    if not string in containers.BACKENDS:
        raise ArgumentTypeError(
            "Backend {} is not available on this machine".format(string))

    return string


def _argument_path(string):
    """Argument type callback.
    Asserts that the string corresponds to an existing path."""
    path = Path(string.strip())

    if not path.exists():
        raise ArgumentTypeError("File {} does not exist".format(
            path.as_posix()))

    return path


def _argument_path_comma_list(string):
    """Argument type callback.
    Asserts that the string corresponds to a list of existing paths."""
    return [_argument_path(data) for data in string.split(',')]


def compute_libs(lib_list, container):
    """Necessary library computation.

    This method will first determine what libraries are available 
    inside the container, then list the dependencies of the requested imports.
    All of the necessary dependencies that are not present in the container
    will get bound."""
    output = container.run(['ldconfig', '-p'], redirect_stdout=True)
    present_in_container = [
        line.strip().split(' ')[0] for line in output.split('\n')[1:]
    ]
    selected = {}

    for path in lib_list:
        container.add_ld_preload("{}/{}".format(HOST_LIBS_DIR, path.name))
        dependencies = util.list_dependencies(path)
        for dependency, data in dependencies.items():
            if dependency not in present_in_container and data['path']:
                selected.update({dependency: data['path']})

    for path in selected.values():
        container.bind_file(path,
                            dest="{}/{}".format(HOST_LIBS_DIR,
                                                Path(path).name),
                            options='ro')


class ExecuteCommand(AbstractCommand):
    """``execute`` subcommand."""
    def _construct_parser(self):
        usage = "%s [arguments] <command> [command_arguments]" % self.command
        parser = arguments.get_parser(prog=self.command,
                                      usage=usage,
                                      description=self.summary)
        parser.add_argument(
            '-d',
            '--dry-run',
            help="Do nothing, print out what would be done instead",
            default=False,
            dest='dry_run',
            action="store_true")

        parser.add_argument('-s',
                            '--slave',
                            help="Format error message for machine parsing",
                            default=False,
                            dest='slave',
                            action="store_true")

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

        return parser

    def main(self, argv):
        args = self._parse_args(argv)
        container = containers.Container(backend=args.backend,
                                         image=args.image)
        if args.slave:
            variables.STATUS = variables.SLAVE

        if args.libraries:
            compute_libs(args.libraries, container)
            container.add_ld_library_path(HOST_LIBS_DIR)

        if args.files:
            for path in args.files:
                container.bind_file(path, dest=path, options='ro')

        if args.dry_run:
            variables.DRY_RUN = True

        container.run(args.cmd, redirect_stdout=False)

        return EXIT_SUCCESS


COMMAND = ExecuteCommand(
    __name__,
    summary_fmt=
    "Execute a command in a container with a tailor-made environment.")
