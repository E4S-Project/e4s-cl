"""Execute command

Definition of arguments and hooks related to the execute command,
file import calculations, and execution of a program passed as an
argument.
"""

from pathlib import Path
from argparse import ArgumentTypeError
from e4s_cl import EXIT_SUCCESS, EXIT_FAILURE, E4S_CL_SCRIPT
from e4s_cl import logger
from e4s_cl.util import ldd
from e4s_cl.variables import is_debug
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


def filter_libraries(library_paths, blacklist=[]):
    selected = {}

    for path in library_paths:
        # Use a ldd parser to grab all the dependencies of
        # the requested library
        # format:
        #   { name(str): path(str) }
        dependencies = ldd(path)

        # Add the library itself as a potential import
        dependencies.update({path.name: {'path': path.as_posix()}})

        for soname, info in dependencies.items():
            # Add if not present in the container but present on the host
            if (soname not in blacklist) and info.get('path'):
                selected.update({soname: info.get('path')})

    return selected.values()


def select_libraries(library_paths, container):
    """Necessary library computation.

    library_paths is a list of pathlib.Path objects

    This method will first determine what libraries are available 
    inside the container, then determine which library import protocol
    needs to be used.
    """

    # Compute the list of sonames available in the container
    output = container.run(['ldconfig', '-p'], redirect_stdout=True)
    present_in_container = [
        line.strip().split(' ')[0] for line in output.split('\n')[1:]
    ]

    method = filter_libraries

    return method(library_paths, blacklist=present_in_container)


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
            return EXIT_FAILURE

        if args.libraries:
            for local_path in select_libraries(args.libraries, container):
                container.bind_file(local_path,
                                    dest="{}/{}".format(
                                        HOST_LIBS_DIR,
                                        Path(local_path).name),
                                    options='ro')
            container.add_ld_library_path(HOST_LIBS_DIR)

        if args.files:
            for path in args.files:
                container.bind_file(path, dest=path, options='ro')

        if is_debug():
            container.bind_env_var('LD_DEBUG', 'files')

        container.run(args.cmd, redirect_stdout=False)

        return EXIT_SUCCESS


COMMAND = ExecuteCommand(
    __name__,
    summary_fmt=
    "Execute a command in a container with a tailor-made environment.")
