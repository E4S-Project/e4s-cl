"""
The :code:`launch` command is responsible for executing commands in containers with the requested MPI environment.

Running a command is done by prefixing a regular MPI launcher command with :code:`e4s-cl launch`.

Using profiles
^^^^^^^^^^^^^^

The preferred way of passing options is by using a \
:ref:`selected profile<profile_select>` or profile specified with the \
:code:`--profile` option. This way, the contents of the given profile are \
implicitly used, bypassing the need to specify any of the options manually. \
However, options given on the command line options have precedence over \
profiles' fields.

MPI translation
^^^^^^^^^^^^^^^

In case the MPI library used on the host and container do not belong to the \
same family, the :code:`--from` option can be used to specify which MPI family \
the binary was compiled with. **e4s-cl** will then take measures to translate \
MPI calls from the binary's MPI to the one passed as an argument. This is done \
using `Wi4MPI <https://github.com/cea-hpc/wi4mpi>`_.
"""

import os
import shlex
from pathlib import Path
from argparse import Namespace
from typing import Tuple, List, Optional
from dataclasses import (dataclass, field)
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
                              WI4MPI_METADATA, _MPIFamily)
from e4s_cl.cf.wi4mpi.install import (WI4MPI_DIR, install_wi4mpi)

from e4s_cl.cli.commands.__execute import COMMAND as EXECUTE_COMMAND

LOGGER = logger.get_logger(__name__)
_SCRIPT_CMD = os.path.basename(E4S_CL_SCRIPT)


@dataclass
class Parameters:
    image: str = None
    backend: str = None
    source: Path = None
    libraries: set = field(default_factory=set)
    files: set = field(default_factory=set)
    wi4mpi: Path = None


def _parameters(args: dict) -> Parameters:
    """Generate compound parameters by merging profile and cli arguments
    The profile's parameters have less priority than the ones specified on
    the command line."""
    if isinstance(args, Namespace):
        args = vars(args)

    profile_data = dict(args.get('profile', {}))

    params = Parameters()

    for attribute, factory in [
        ('image', str),
        ('backend', str),
        ('libraries', lambda x: set(map(Path, x))),
        ('files', lambda x: set(map(Path, x))),
        ('source', lambda x: Path(x) if x else None),
        ('wi4mpi', lambda x: Path(x) if x else None),
    ]:
        value = args.get(attribute) or profile_data.get(attribute)
        if value is not None:
            setattr(params, attribute, factory(value))

    return params


def _format_execute(parameters: Parameters) -> List[str]:
    execute_command = shlex.split(str(EXECUTE_COMMAND))
    execute_command = [E4S_CL_SCRIPT] + execute_command[1:]

    if logger.debug_mode():
        execute_command = [execute_command[0], '-v'] + execute_command[1:]

    for attr in ['image', 'backend', 'source', 'wi4mpi']:
        value = getattr(parameters, attr, None)
        if value:
            execute_command += [f"--{attr}", str(value)]

    for attr in ['libraries', 'files']:
        value = getattr(parameters, attr, None)
        if value:
            execute_command += [f"--{attr}", ",".join(map(str, value))]

    return execute_command


def _setup_wi4mpi(
    parameters: Parameters,
    translation: Tuple,
    family_metadata: _MPIFamily,
    mpi_libraries: List[Path],
) -> Tuple[List[str], List[str]]:
    """Prepare the environment for the use of Wi4MPI
    - Set or update 'wi4mpi' in the parameters
    - Update the environment variables:
      + WI4MPI_ROOT
      + WI4MPI_FROM
      + WI4MPI_TO
      + <LIBRARY>_ROOT
      + WI4MPI_RUN_MPI_C_LIB
      + WI4MPI_RUN_MPI_F_LIB
      + WI4MPI_RUN_MPIIO_C_LIB
      + WI4MPI_RUN_MPIIO_F_LIB
    - Prepare the wi4mpi launcher for the final command
    """

    # Locate the Wi4MPI installation - either provided on the cli or default
    if parameters.wi4mpi is None:
        wi4mpi_install = install_wi4mpi()
        if wi4mpi_install:
            parameters.wi4mpi = wi4mpi_install
        else:
            LOGGER.error(
                "Wi4MPI is required for this configuration, but installation failed"
            )
            return []

    def locate(soname: str, available: List[Path]) -> Optional[Path]:
        matches = set(filter(lambda x: x.name.startswith(soname), available))
        search_directories = set(map(lambda x: x.resolve().parent, available))

        # If a match exists in the given libraries
        if matches:
            return matches.pop()

        # Search the libraries' directories for the soname
        for directory in search_directories:
            matches = set(directory.glob(f"{soname}*"))
            if matches:
                return matches.pop()

        LOGGER.debug(
            "Failed to locate %(soname)s in %(directories)s",
            dict(
                soname=soname,
                directories=search_directories,
            ),
        )

        return None

    # Find the entry C and Fortran MPI libraries
    run_c_lib = locate(family_metadata.mpi_c_soname, mpi_libraries)
    run_f_lib = locate(family_metadata.mpi_f_soname, mpi_libraries)
    if not (run_c_lib and run_f_lib):
        LOGGER.error(
            "Could not determine MPI libraries to use; Wi4MPI use aborted "
            "(no %(c_soname)s or %(f_soname)s in %(list)s)",
            dict(
                c_soname=family_metadata.mpi_c_soname,
                f_soname=family_metadata.mpi_f_soname,
                list=list(mpi_libraries),
            ),
        )
        return []

    # Deduce the MPI installation directory
    mpi_install = install_dir([run_c_lib, run_f_lib])

    parameters.files.add(mpi_install)

    env = {
        'WI4MPI_ROOT': str(parameters.wi4mpi),
        'WI4MPI_FROM': str(translation[0]),
        'WI4MPI_TO': str(translation[1]),
        family_metadata.path_key: str(mpi_install),
        'WI4MPI_RUN_MPI_C_LIB': str(run_c_lib),
        'WI4MPI_RUN_MPI_F_LIB': str(run_f_lib),
        'WI4MPI_RUN_MPIIO_C_LIB': str(run_c_lib),
        'WI4MPI_RUN_MPIIO_F_LIB': str(run_f_lib),
    }

    LOGGER.debug("Wi4MPI environment: %s", env)
    for key, value in env.items():
        os.environ[key] = value

    # Add the Wi4MPI --from --to options
    wi4mpi_bin_path = parameters.wi4mpi / 'bin'
    wi4mpi_call = shlex.split(
        f"{wi4mpi_bin_path / 'wi4mpi'} -f {translation[0]} -t {translation[1]}"
    )

    return wi4mpi_call


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
            '--backend',
            help="Container backend to use to launch the image." +
            f" Available backends are: {', '.join(EXPOSED_BACKENDS)}",
            metavar='technology',
            dest='backend',
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
            '--wi4mpi',
            type=arguments.posix_path,
            help="Path towards a Wi4MPI installation to use",
            metavar='installation',
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
            if not getattr(parameters, field, None):
                self.parser.error(
                    f"Missing field: '{field}'. Specify it using the "
                    "appropriate option or by selecting a profile.")

        launcher, program = interpret(args.cmd)

        for path in get_reserved_directories(launcher):
            if path not in parameters.files:
                parameters.files.add(path)

        binary_mpi_family = getattr(args, 'from', None)
        profile_mpi_libraries = filter_mpi_libs(parameters.libraries)
        profile_mpi_family = detect_mpi(profile_mpi_libraries)

        if profile_mpi_family:
            LOGGER.debug(
                "Parameters contain the MPI library '%s'",
                profile_mpi_family,
            )
        else:
            LOGGER.debug(
                "No single MPI family could be detected in the parameters")

        translation = (binary_mpi_family, wi4mpi_qualifier(profile_mpi_family))
        wi4mpi_call = []
        if translation in SUPPORTED_TRANSLATIONS:
            target_mpi_data = wi4mpi_identify(profile_mpi_family.vendor)
            wi4mpi_call = _setup_wi4mpi(
                parameters,
                translation,
                target_mpi_data,
                profile_mpi_libraries,
            )

            # Relay the environment if OpenMPI is used
            if (profile_mpi_family.vendor == "Open MPI"
                    and Path(launcher[0]).name == "mpirun"):
                launcher += shlex.split("-x WI4MPI_ROOT "
                                        f"-x {target_mpi_data.path_key} "
                                        "-x WI4MPI_RUN_MPI_C_LIB "
                                        "-x WI4MPI_RUN_MPI_F_LIB "
                                        "-x WI4MPI_RUN_MPIIO_C_LIB "
                                        "-x WI4MPI_RUN_MPIIO_F_LIB")

        execute_command = _format_execute(parameters)
        full_command = [*launcher, *wi4mpi_call, *execute_command, *program]

        if variables.is_dry_run():
            print(' '.join(map(str, full_command)))
            return EXIT_SUCCESS

        retval, _ = run_e4scl_subprocess(full_command)

        return retval


SUMMARY = "Launch a process in a container with a tailored environment."
COMMAND = LaunchCommand(__name__, summary_fmt=SUMMARY)
