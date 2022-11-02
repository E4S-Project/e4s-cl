"""
E4S Container Launcher is a accessory launcher to ensure host MPI libraries \
are used in containers. It wraps around a valid MPI launch command \
to work.

The preferred way of launching a command is by using a selected or specified profile. \
That way, the fields of the target profile are implicitly used, bypassing the \
need to specify any of the options manually.

If the user intends to use a modified version of an existing profile, specifying \
the difference as a command line option can be efficient as command line options \
have precedence over profiles' fields.

.. admonition:: Using a :ref:`selected profile<profile_select>`

    When a :ref:`profile<profile>` is selected, it will be used if no \
:code:`--profile` option is passed.

The minimal options that must be given in order to run without a selected \
or specified profile are:

* A container image;
* A container technology to run the image with.

Other options then influence the execution:

* Arguments passed to :code:`--files` will be made available in the container;
* Libraries passed to :code:`--libraries` will be loaded;
* A script passed to :code:`--source` will be run in the container before any \
other command.


.. admonition:: Implicit sub-command

    When **e4s-cl** is called without a proper sub-command (:code:`launch` or \
:code:`profile`), the program will implicitly use the :code:`launch` \
sub-command. This requires a complete profile to be selected as no launch \
arguments can be passed.
"""

import os
import shlex
from pathlib import Path
from argparse import Namespace
from typing import Tuple, List
from e4s_cl import EXIT_SUCCESS, E4S_CL_SCRIPT
from e4s_cl import logger, variables
from e4s_cl.cli import arguments
from e4s_cl.util import run_e4scl_subprocess
from e4s_cl.cli.command import AbstractCommand
from e4s_cl.cf.launchers import interpret, get_reserved_directories
from e4s_cl.model.profile import Profile
from e4s_cl.cf.containers import EXPOSED_BACKENDS
from e4s_cl.cf.detect_mpi import (detect_mpi, install_dir, filter_mpi_libs)
from e4s_cl.cf.wi4mpi import (wi4mpi_adapt_arguments, SUPPORTED_TRANSLATIONS,
                              wi4mpi_qualifier, wi4mpi_identify,
                              WI4MPI_METADATA)
from e4s_cl.cf.wi4mpi.install import (WI4MPI_DIR, install_wi4mpi)

from e4s_cl.cli.commands.__execute import COMMAND as EXECUTE_COMMAND

LOGGER = logger.get_logger(__name__)
_SCRIPT_CMD = os.path.basename(E4S_CL_SCRIPT)


def _parameters(args):
    """Generate compound parameters by merging profile and cli arguments
    The profile's parameters have less priority than the ones specified on
    the command line."""
    if isinstance(args, Namespace):
        args = vars(args)

    default_profile = dict(image='',
                           backend='',
                           libraries=[],
                           files=[],
                           source='')

    parameters = dict(args.get('profile', default_profile))

    for attr in ['image', 'backend', 'libraries', 'files', 'source']:
        if args.get(attr, None):
            parameters.update({attr: args[attr]})

    return parameters


def _format_execute(parameters):
    execute_command = shlex.split(str(EXECUTE_COMMAND))

    execute_command = [E4S_CL_SCRIPT] + execute_command[1:]

    if logger.debug_mode():
        execute_command = [execute_command[0], '-v'] + execute_command[1:]

    for attr in ['image', 'backend', 'source']:
        value = parameters.get(attr, None)
        if value:
            execute_command += [f"--{attr}", str(value)]

    for attr in ['libraries', 'files']:
        value = parameters.get(attr, None)
        if value:
            execute_command += [f"--{attr}", ",".join(map(str, value))]

    wi4mpi_root = parameters.get('wi4mpi', None)
    if wi4mpi_root:
        execute_command += ['--wi4mpi', wi4mpi_root]

    return execute_command


def _setup_wi4mpi(launcher, parameters, translation, profile_mpi_install,
                  profile_mpi_family) -> Tuple[List[str], List[str]]:
    """Overwrite the launcher and prepare the environment if Wi4MPI is required
    for this configuration"""
    bin_path = os.environ.get('PATH')

    # Locate the Wi4MPI installation - either provided on the cli or default
    wi4mpi_root = parameters.get('wi4mpi')
    if not wi4mpi_root:
        wi4mpi_root = install_wi4mpi(WI4MPI_DIR / 'install')
        if wi4mpi_root:
            parameters['wi4mpi'] = str(wi4mpi_root)
        else:
            LOGGER.error(
                "Wi4MPI is required for this configuration, but installation failed"
            )
            return launcher, []

    wi4mpi_bin_path = Path(wi4mpi_root) / 'bin'

    target_mpi_data = wi4mpi_identify(profile_mpi_family.vendor)

    os.environ['WI4MPI_ROOT'] = str(wi4mpi_root)
    os.environ[target_mpi_data.path_key] = str(profile_mpi_install)

    # Add the Wi4MPI --from --to options
    wi4mpi_call = shlex.split(
        f"{wi4mpi_bin_path / 'wi4mpi'} -f {translation[0]} -t {translation[1]}"
    )

    # Pass the necessary environment if OpenMPI is used, other launchers do it as default
    if profile_mpi_family.vendor == "Open MPI" \
            and Path(launcher[0]).name == "mpirun":
        launcher += shlex.split(
            f"-x WI4MPI_ROOT -x {target_mpi_data.path_key}")

    # Validate the command line
    return launcher, wi4mpi_call


class LaunchCommand(AbstractCommand):
    """``launch`` subcommand."""

    def _construct_parser(self):
        usage = f"{self.command} [arguments] [launcher] [launcher_arguments] [--] <command> [command_arguments]"
        parser = arguments.get_parser(
            prog=self.command,
            usage=usage,
            description=self.summary,
        )
        parser.add_argument(
            '--profile',
            type=arguments.single_defined_object(Profile, 'name'),
            help=
            "Profile to use. Its fields will be used by default, but any other argument will override them",
            default=Profile.selected().get('name', arguments.SUPPRESS),
            metavar='profile',
        )

        parser.add_argument(
            '--image',
            type=str,
            help="Path to the container image to run the program in",
            metavar='image',
        )

        parser.add_argument(
            '--source',
            type=arguments.posix_path,
            help="Path to a bash script to source before execution",
            metavar='source',
        )

        parser.add_argument(
            '--files',
            type=arguments.posix_path_list,
            help="Comma-separated list of files to bind",
            metavar='files',
        )

        parser.add_argument(
            '--libraries',
            type=arguments.posix_path_list,
            help="Comma-separated list of libraries to bind",
            metavar='libraries',
        )

        parser.add_argument(
            '--backend',
            help="Container backend to use to launch the image." +
            f" Available backends are: {', '.join(EXPOSED_BACKENDS)}",
            metavar='technology',
            dest='backend',
        )

        mpi_families = set(map(lambda x: x.cli_name, WI4MPI_METADATA))
        parser.add_argument(
            '--from',
            type=str.lower,
            choices=mpi_families,
            help=
            "MPI family the command was intended to be run. Use this argument "
            "to toggle MPI call translation. Available families: " +
            ", ".join(mpi_families),
            default=arguments.SUPPRESS,
            metavar='mpi-family',
        )

        parser.add_argument(
            'cmd',
            help="Executable command, e.g. './a.out'",
            metavar='command',
            nargs=arguments.REMAINDER,
        )
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
        for field in ['backend', 'image']:
            if not parameters.get(field, None):
                self.parser.error(
                    f"Missing field: '{field}'. Specify it using the "
                    "appropriate option or by selecting a profile.")

        launcher, program = interpret(args.cmd)

        for path in get_reserved_directories(launcher):
            files = parameters.get('files', [])

            if path.as_posix() not in files:
                files.append(path.as_posix())

            parameters['files'] = files

        binary_mpi_family = getattr(args, 'from', None)
        profile_mpi_libraries = filter_mpi_libs(
            map(Path, parameters.get('libraries', [])))
        profile_mpi_family = detect_mpi(profile_mpi_libraries)
        profile_mpi_install = install_dir(profile_mpi_libraries)

        if profile_mpi_family:
            LOGGER.debug(
                "Parameters contain the MPI library '%(mpi_family)s' installed "
                "in '%(install_dir)s'",
                dict(
                    mpi_family=profile_mpi_family,
                    install_dir=str(profile_mpi_install),
                ))
        else:
            LOGGER.debug(
                "No single MPI family could be detected in the parameters")

        translation = (binary_mpi_family, wi4mpi_qualifier(profile_mpi_family))
        wi4mpi_call = []
        if launcher and translation in SUPPORTED_TRANSLATIONS:
            launcher, wi4mpi_call = _setup_wi4mpi(
                launcher,
                parameters,
                translation,
                profile_mpi_install,
                profile_mpi_family,
            )

        execute_command = _format_execute(parameters)
        full_command = [*launcher, *wi4mpi_call, *execute_command, *program]

        if variables.is_dry_run():
            print(' '.join(map(str, full_command)))
            return EXIT_SUCCESS

        retval, _ = run_e4scl_subprocess(full_command)

        return retval


SUMMARY = "Launch a process in a container with a tailored environment."
COMMAND = LaunchCommand(__name__, summary_fmt=SUMMARY)
