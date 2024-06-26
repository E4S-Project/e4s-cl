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
from e4s_cl import (
    E4S_CL_SCRIPT,
    EXIT_SUCCESS,
    config,
    logger,
    variables,
)
from e4s_cl.cli import arguments
from e4s_cl.util import run_e4scl_subprocess
from e4s_cl.cli.command import AbstractCommand
from e4s_cl.cf.launchers import interpret, get_reserved_directories
from e4s_cl.model.profile import Profile
from e4s_cl.cf.containers import EXPOSED_BACKENDS
from e4s_cl.cf.detect_mpi import (
    detect_mpi,
    filter_mpi_libs,
    library_install_dir,
)
from e4s_cl.cf.wi4mpi import (
    MPIFamily,
    SUPPORTED_TRANSLATIONS,
    WI4MPI_ENVIRONMENT_VARIABLES,
    WI4MPI_METADATA,
    WI4MPI_SOURCES,
    wi4mpi_find_libraries,
    wi4mpi_get_metadata,
    wi4mpi_identify,
    wi4mpi_prepare_environment_interface,
    wi4mpi_prepare_environment_preload,
    wi4mpi_qualifier,
)
from e4s_cl.cf.wi4mpi.install import install_wi4mpi

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

    for attr in ['image', 'backend', 'source']:
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
    family_metadata: MPIFamily,
    mpi_libraries: List[Path],
) -> List[str]:
    """Prepare the environment for the use of Wi4MPI
    - Set or update 'wi4mpi' in the parameters
    - Prepare the wi4mpi launcher for the final command
    """

    LOGGER.debug("Setting up Wi4MPI to translate '%s' to '%s' (%s)",
                 *translation, family_metadata.vendor_name)

    # Switch translation from mvapich to mpich, as wi4mpi doesn't recognise
    # mvapich as a separate flag
    if 'mvapich' in translation:
        translation = [vendor.replace('mvapich', 'mpich') for vendor in translation]

    # Locate the Wi4MPI installation and store it in parameters
    if parameters.wi4mpi is None:
        target_dir = Path(config.CONFIGURATION.wi4mpi_install_directory)
        LOGGER.debug("Target: %s", target_dir)
        wi4mpi_install = install_wi4mpi(target_dir)
        if wi4mpi_install:
            parameters.wi4mpi = wi4mpi_install
        else:
            LOGGER.error(
                "Wi4MPI is required for this configuration, but installation failed"
            )
            return []

    run_c_lib, run_f_lib = wi4mpi_find_libraries(family_metadata,
                                                 mpi_libraries)

    if not (run_c_lib and run_f_lib):
        LOGGER.error(
            "Could not determine MPI libraries to use; Wi4MPI use aborted "
            "(no %(c_soname)s or %(f_soname)s in %(list)s)",
            {
                "c_soname": family_metadata.mpi_c_soname,
                "f_soname": family_metadata.mpi_f_soname,
                "list": list(mpi_libraries),
            },
        )
        return []

    # Deduce the MPI installation directory, add it to the imported files
    mpi_install_dir = library_install_dir([run_c_lib, run_f_lib])
    if mpi_install_dir:
        parameters.files.add(mpi_install_dir)

    wi4mpi_wrapper = parameters.wi4mpi / 'bin' / 'wi4mpi'

    # Prepare the environment; add the Wi4MPI --from --to options
    if translation[0] == 'interface':
        wi4mpi_prepare_environment_interface(
            parameters.wi4mpi,
            family_metadata,
            mpi_install_dir,
            run_c_lib,
            run_f_lib,
        )
        wi4mpi_call = shlex.split(f"{wi4mpi_wrapper} -t {translation[1]}")
    else:
        wi4mpi_prepare_environment_preload(
            parameters.wi4mpi,
            translation[0],
            family_metadata,
            mpi_install_dir,
            run_c_lib,
            run_f_lib,
        )
        wi4mpi_call = shlex.split(
            f"{wi4mpi_wrapper} -f {translation[0]} -t {translation[1]}")

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

        parser.add_argument(
            '--from',
            type=str.lower,
            choices=WI4MPI_SOURCES,
            help=
            "MPI family the command was intended to be run. Use this argument "
            "to toggle MPI call translation. Available families: " +
            ", ".join(WI4MPI_SOURCES),
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
            self.parser.error("No executable was specified.")

        # Merge profile and cli arguments to get a definitive list of arguments
        parameters = _parameters(args)

        # Ensure the minimum fields required for launch are present
        for _field in ['backend', 'image']:
            if not getattr(parameters, _field, None):
                if getattr(parameters, 'backend',None) == 'barebones':
                    continue
                self.parser.error(
                    f"Missing field: '{_field}'. Specify it using the "
                    "appropriate option or by selecting a profile.")

        launcher, program = interpret(args.cmd)

        for path in get_reserved_directories(launcher):
            if path not in parameters.files:
                parameters.files.add(path)

        wi4mpi_call = []

        # Source MPI family from the command line
        binary_mpi_family = getattr(args, 'from', None)
        # MPI shared objects from the parameters
        profile_mpi_libraries = filter_mpi_libs(parameters.libraries)
        # MPI family from the parameters (MPIIdentifier)
        profile_mpi_family = detect_mpi(profile_mpi_libraries)
        # MPI family Wi4MPI data from the parameters (MPIFamily)
        profile_mpi_family_data = wi4mpi_get_metadata(profile_mpi_family)

        if profile_mpi_family:
            LOGGER.debug(
                "Parameters contain the MPI library '%s'",
                profile_mpi_family,
            )
        else:
            LOGGER.debug(
                "No MPI family could be identified from the parameters")

        # If the parameters' MPI family is understood by Wi4MPI
        if profile_mpi_family_data:
            # Check the translation is supported
            translation = (binary_mpi_family, profile_mpi_family_data.cli_name)
            if translation in SUPPORTED_TRANSLATIONS:
                # Setup the environment and return the command line wrapper
                wi4mpi_call = _setup_wi4mpi(
                    parameters,
                    translation,
                    profile_mpi_family_data,
                    profile_mpi_libraries,
                )

                # Explicitly pass the environment if OpenMPI's launcher is used
                if (profile_mpi_family.vendor == "Open MPI"
                        and Path(launcher[0]).name == "mpirun"):
                    for varname in WI4MPI_ENVIRONMENT_VARIABLES:
                        if varname in os.environ.keys():
                            launcher.extend(shlex.split(f"-x {varname}"))

        execute_command = _format_execute(parameters)
        full_command = [*launcher, *wi4mpi_call, *execute_command, *program]

        if variables.is_dry_run():
            print(' '.join(map(str, full_command)))
            return EXIT_SUCCESS

        retval, _ = run_e4scl_subprocess(full_command)
        return retval


SUMMARY = "Launch a process in a container with a tailored environment."
COMMAND = LaunchCommand(__name__, summary_fmt=SUMMARY)
