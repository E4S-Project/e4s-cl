"""Execute command

Definition of arguments and hooks related to the execute command,
file import calculations, and execution of a program passed as an
argument.
"""

from pathlib import Path
from argparse import ArgumentTypeError
from e4s_cl import EXIT_SUCCESS, E4S_CL_SCRIPT
from e4s_cl import logger
from e4s_cl.util import ldd
from e4s_cl.cli import arguments
from e4s_cl.cli.command import AbstractCommand
from e4s_cl.cf.containers import Container, BackendNotAvailableError

LOGGER = logger.get_logger(__name__)
_SCRIPT_CMD = Path(E4S_CL_SCRIPT).name

HOST_LIBS_DIR = Path('/hostlibs/').as_posix()


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

    lib_list is a list of Path objects

    This method will first determine what libraries are available 
    inside the container, then list the dependencies of the requested imports.
    All of the necessary dependencies that are not present in the container
    will get bound."""
    output = container.run(['ldconfig', '-p'], redirect_stdout=True)
    present_in_container = [
        line.strip().split(' ')[0] for line in output.split('\n')[1:]
    ]
    selected = {}

    for lib_path in lib_list:
        # Use a ldd parser to grab all the dependencies of
        # the requested library
        dependencies = ldd(lib_path)
        for dependency, data in dependencies.items():
            # Add it only if it is not present in the container
            if dependency not in present_in_container and data['path']:
                selected.update({dependency: data['path']})

        # For the entrypoint, the requested library, add it no matter what
        # (to override the internal version) then add it to LD_PRELOAD
        selected.update({lib_path.name: lib_path.as_posix()})
        container.add_ld_preload("{}/{}".format(HOST_LIBS_DIR, lib_path.name))

    for local_path in selected.values():
        container.bind_file(local_path,
                            dest="{}/{}".format(HOST_LIBS_DIR,
                                                Path(local_path).name),
                            options='ro')


class ExecuteCommand(AbstractCommand):
    """``execute`` subcommand."""
    def _construct_parser(self):
        usage = "%s [arguments] <command> [command_arguments]" % self.command
        parser = arguments.get_parser(prog=self.command,
                                      usage=usage,
                                      description=self.summary)
        parser.add_argument("--backend",
                            type=str,
                            dest='backend',
                            required=True,
                            help="Specify the container executable",
                            metavar='executable')

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
        try:
            container = Container(executable=args.backend, image=args.image)
        except BackendNotAvailableError as e:
            self.parser.error("Executable %s not available" % args.backend)

        if args.libraries:
            compute_libs(args.libraries, container)
            container.add_ld_library_path(HOST_LIBS_DIR)

        if args.files:
            for path in args.files:
                container.bind_file(path, dest=path, options='ro')

        container.run(args.cmd, redirect_stdout=False)

        return EXIT_SUCCESS


COMMAND = ExecuteCommand(
    __name__,
    summary_fmt=
    "Execute a command in a container with a tailor-made environment.")
