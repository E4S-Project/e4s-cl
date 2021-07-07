"""
E4S Container Launcher is a accessory launcher to ensure host MPI libraries \
are used in containers. It wraps around a valid MPI launch command \
to work.

The minimal options that must be given in order to run are:

* A container image;
* A container technology to run the image with.

Other options then influence the execution:

* Arguments passed to :code:`--files` will be made available in the container;
* Libraries passed to :code:`--libraries` will be loaded;
* A script passed to :code:`--source` will be run in the container before any \
other command.

All of these options can be bypassed by passing a :ref:`profile<profile>`.
The fields of the target :ref:`profile<profile>` are then implicitly used for \
each of the above options.

.. admonition:: Using a :ref:`selected profile<profile_select>`

    When a :ref:`profile<profile>` is selected, it will be used if no \
:code:`--profile` option is passed. Command line options have precedence \
over profiles' fields.

"""

import os
from argparse import Namespace
from e4s_cl import EXIT_SUCCESS, E4S_CL_SCRIPT
from e4s_cl import logger, variables
from e4s_cl.cli import arguments
from e4s_cl.util import create_subprocess_exp
from e4s_cl.cli.command import AbstractCommand
from e4s_cl.cf.launchers import interpret
from e4s_cl.model.profile import Profile
from e4s_cl.cf.containers import EXPOSED_BACKENDS

from e4s_cl.cli.commands.__execute import COMMAND as execute_cmd

LOGGER = logger.get_logger(__name__)
_SCRIPT_CMD = os.path.basename(E4S_CL_SCRIPT)


def _parameters(args):
    """Generate compound parameters by merging profile and cli arguments
    The profile's parameters have less priority than the ones specified on
    the command line."""
    if isinstance(args, Namespace):
        args = vars(args)

    parameters = dict(args.get('profile', {}))

    for attr in ['image', 'backend', 'libraries', 'files']:
        if args.get(attr, None):
            parameters.update({attr: args[attr]})

    return parameters


def _format_execute(parameters):
    execute_command = str(execute_cmd).split()

    # Insert a top-level e4s option between the script name and the subcommand
    execute_command = [E4S_CL_SCRIPT, '--slave'] + execute_command[1:]

    if logger.debug_mode():
        execute_command = [execute_command[0], '-v'] + execute_command[1:]

    for attr in ['image', 'backend', 'source']:
        if parameters.get(attr, None):
            execute_command += ["--{}".format(attr), parameters[attr]]

    for attr in ['libraries', 'files']:
        if parameters.get(attr, None):
            execute_command += [
                "--{}".format(attr), ",".join(parameters[attr])
            ]

    return execute_command


class LaunchCommand(AbstractCommand):
    """``launch`` subcommand."""
    def _construct_parser(self):
        usage = "%s [arguments] [launcher] [launcher_arguments] [--] <command> [command_arguments]" % self.command
        parser = arguments.get_parser(prog=self.command,
                                      usage=usage,
                                      description=self.summary)
        parser.add_argument(
            '--profile',
            type=arguments.defined_object(Profile, 'name'),
            help=
            "Profile to use. Its fields will be used by default, but any other argument will override them",
            default=Profile.selected().get('name', arguments.SUPPRESS),
            metavar='profile')

        parser.add_argument(
            '--image',
            type=str,
            help="Path to the container image to run the program in",
            metavar='image')

        parser.add_argument(
            '--source',
            type=arguments.posix_path,
            help="Path to a bash script to source before execution",
            metavar='source')

        parser.add_argument('--files',
                            type=arguments.posix_path_list,
                            help="Comma-separated list of files to bind",
                            metavar='files')

        parser.add_argument('--libraries',
                            type=arguments.posix_path_list,
                            help="Comma-separated list of libraries to bind",
                            metavar='libraries')

        parser.add_argument(
            '--backend',
            help="Container backend to use to launch the image." +
            " Available backends are: %s" % ", ".join(EXPOSED_BACKENDS),
            metavar='technology',
            dest='backend')

        parser.add_argument('cmd',
                            help="Executable command, e.g. './a.out'",
                            metavar='command',
                            nargs=arguments.REMAINDER)
        return parser

    def main(self, argv):
        args = self._parse_args(argv)

        if getattr(args, 'profile', None) and '--profile' not in argv:
            LOGGER.info("Using selected profile %s", args.profile.get('name'))

        if not args.cmd:
            self.parser.error("No command given")

        # Merge profile and cli arguments to get a definitive list of arguments
        parameters = _parameters(args)

        # Ensure the minimum fields required for launch are present
        for field in {'backend', 'image'}:
            if not parameters.get(field, None):
                self.parser.error("Missing field: '%s'. Specify it using the appropriate option or by selecting a profile." % field)

        launcher, program = interpret(args.cmd)
        execute_command = _format_execute(parameters)

        full_command = launcher + execute_command + program

        if variables.is_dry_run():
            print(' '.join(full_command))
            return EXIT_SUCCESS

        retval, _ = create_subprocess_exp(full_command)

        return retval


SUMMARY = "Launch a process with a tailored environment."

COMMAND = LaunchCommand(__name__, summary_fmt=SUMMARY)
