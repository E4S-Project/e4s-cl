"""
This command is intended to be run once, and will create a \
:ref:`profile<profile>` from the resources made available to it. \
Initialization can be achieved in multiple ways, depending on the \
arguments passed to the command.

In case no method is explicitly invoked, the command attempts MPI library \
analysis, by using the MPI compiler and launcher available in the environment.

Using an installed MPI library
--------------------------------

This initialization method will create a profile from the execution analysis \
of a sample MPI program. A program compiled with the MPI library's compiler \
will run in a debug environment. The opened files and libraries will be \
detected using the :code:`ptrace` system call, and added to the resulting \
profile.

The sample command used depends on the arguments given to **e4s-cl**. An entire command can be passed on the command line, or it will be constructed from the :code:`--mpi`, :code:`--launcher` and :code:`--launcher_args` options.

It is highly encouraged to load the MPI library beforehand using the module \
system available (:code:`spack`/:code:`modules`/:code:`lmod`) to ensure the \
paths and dependencies are valid and loaded.

.. admonition:: The importance of inter-process communication

    This process relies on the execution of a sample MPI program to discover \
    its dependencies. In some cases, a library will lazy-load network \
    libraries, preventing them from being detected. A message will appear in \
    case some limitations were detected.

If no name is passed to :code:`--profile`, a :ref:`profile<profile>` \
name will be generated from the version of the found MPI library.

Using a system name
-----------------------

If the current system is supported, use the :code:`--system` argument to \
flag its use. The available values are listed when using \
:code:`e4s-cl init -h`. In order to have the system-specific profiles \
available (and listed as available), the :code:`E4SCL_TARGETSYSTEM=<system>` \
flag needs to be used when installing the project.

Examples
--------

Initializing using MPI resources from the environment:

.. code::

    module load mpich
    e4s-cl init

Initializing by passing a MPI command:

.. code::

    module load mpich
    e4s-cl init mpirun -np 2 ./sample-program

Using a library installed on the system in :code:`/packages`:

.. code::

    e4s-cl init --mpi /packages/mpich --profile mpich
"""

import os
import json
import tempfile
import subprocess
import shlex
from pathlib import Path
from typing import (List, Optional)
from sotools.linker import resolve
from e4s_cl import (
    E4S_CL_MPI_TESTER_SCRIPT_NAME,
    E4S_CL_SCRIPT,
    EXIT_FAILURE,
    EXIT_SUCCESS,
    INIT_TEMP_PROFILE_NAME,
)
from e4s_cl import logger, util
from e4s_cl.cf.assets import precompiled_binaries, builtin_profiles
from e4s_cl.cf.detect_mpi import (
    filter_mpi_libs,
    library_install_dir,
    profile_mpi_name,
)
from e4s_cl.cf.containers import guess_backend, EXPOSED_BACKENDS
from e4s_cl.cli.arguments import (
    REMAINDER,
    SUPPRESS,
    binary_in_path,
    get_parser,
    posix_path,
)
from e4s_cl.cli.command import AbstractCommand
from e4s_cl.cli.commands.profile.detect import COMMAND as detect_command
from e4s_cl.error import (UniqueAttributeError, ModelError)
from e4s_cl.model.profile import Profile
from e4s_cl.sample import PROGRAM

LOGGER = logger.get_logger(__name__)
_SCRIPT_CMD = os.path.basename(E4S_CL_SCRIPT)


def _check_mpirun(executable):
    """
    Run hostname with the launcher and list the affected nodes
    """
    hostname_bin = util.which('hostname')
    if not hostname_bin:
        return

    with subprocess.Popen([executable, hostname_bin],
                          stdout=subprocess.PIPE) as proc:
        proc.wait()

        hostnames = {hostname.strip() for hostname in proc.stdout.readlines()}

    if len(hostnames) == 1:
        LOGGER.warning(
            "The target launcher %s uses a single host by default, "
            "which may tamper with the library discovery. Consider "
            "running `%s` using mpirun specifying multiple hosts.", executable,
            str(detect_command))


def _profile_from_args(args) -> dict:
    """
    Create a dictionnary with all the profile related information passed as arguments
    """
    data = {}

    for attr in ['image', 'backend', 'source', 'wi4mpi']:
        value = getattr(args, attr, None)
        if value:
            data[attr] = value

    # Determine the backend if possible
    if data.get('image') and not data.get('backend'):
        data['backend'] = guess_backend(args.image)

    # Load data from assets if required
    system = getattr(args, 'system', None)
    if system:
        data = {**data, **builtin_profiles().get(system, {})}

    return data


def _analyze_binary(args):
    # If no profile has been loaded or wi4mpi is not used, then
    # we need to analyze a binary to
    # determine the dynamic dependencies of the library

    command = getattr(args, 'cmd', None)
    if not command:
        command = _generate_command(args)

    if not command:
        return EXIT_FAILURE

    # Run the program using the detect command and get a file list
    returncode = detect_command.main(command)

    if returncode != EXIT_SUCCESS:
        LOGGER.error("Tracing of MPI execution failed")
        return EXIT_FAILURE

    return EXIT_SUCCESS


def _find_tester() -> Optional[Path]:
    """
    Locate the MPI tester script. It is installed alongside e4s-cl and is used
    to load and run an MPI library for analysis
    """

    # First look in PATH for the script
    script = util.which(E4S_CL_MPI_TESTER_SCRIPT_NAME)

    if script is None:
        # If installed via pip, the script should be located in the same
        # directory as e4s-cl. Resolve argv[0] to bypass symlinks and look for
        # the file in the parent directory
        install_dir = Path(E4S_CL_SCRIPT).resolve().parent
        installed = Path(install_dir, E4S_CL_MPI_TESTER_SCRIPT_NAME)
        if installed.exists():
            script = installed

    if script is None:
        return None
    return Path(script)


def _generate_command(args) -> List[str]:
    """
    Generate a command from the given args with a launcher and mpi binary
    """
    # Use the MPI environment scripts by default
    launcher = util.which('mpirun')

    # If a library is specified, get the executables
    if getattr(args, 'mpi', None):
        mpirun = Path(args.mpi) / "bin" / "mpirun"
        if mpirun.exists():
            launcher = mpirun.as_posix()

        # Update LD_LIBRARY_PATH if provided path exist
        mpi_lib = Path(args.mpi) / "lib"
        if mpi_lib.exists():
            os.environ["LD_LIBRARY_PATH"] = mpi_lib.as_posix()

    # Use the launcher passed as an argument in priority
    arg_launcher = getattr(args, 'launcher', None)
    if arg_launcher:
        launcher = arg_launcher

    launcher_args = shlex.split(getattr(args, 'launcher_args', ''))

    # Check for launcher and then launch the detect command
    if not launcher:
        LOGGER.error(
            "No MPI launcher detected. Please load an MPI module, use the "
            "`--mpi` or `--launcher` options to specify the launcher program "
            "to use.")
        return []

    # If no arguments were given, check the default behaviour of the launcher
    if not launcher_args:
        _check_mpirun(launcher)

    tester = _find_tester()
    if tester is None:
        raise ValueError("Cannot find tester script !")

    command = [
        launcher,
        *launcher_args,
        tester.as_posix(),
    ]
    LOGGER.info("Tracing MPI execution using:\n%s", command)

    # Run the program using the detect command and get a file list
    return command


def _skip_analysis(args) -> bool:
    """Skip analysis step when certain conditions are met"""

    # If using shifter, do not try to profile a library
    # TODO Allow user to request full initialization
    if getattr(args, 'backend', '') == 'shifter':
        LOGGER.info("Skipping analysis to use shifter modules")
        return False

    return True


def _rename_profile(profile: Profile, requested_name: Optional[str]) -> None:
    """Rename the given profile with a given name or create a special unique
    hash for it"""
    current_name = profile.get('name')
    if current_name == INIT_TEMP_PROFILE_NAME:
        current_name = None

    if ((requested_name == current_name and requested_name is not None)
            or (current_name and requested_name is None)):
        """
        match (requested_name, current_name) with:
            (None, None) -> rename (create hash)
            (None, x) -> pass (keep x)
            (x, None) -> rename (set x)
            (x, y) -> rename (overwrite y with x)
            (x, x) -> pass

        ==> Rename if !((r == c && r != None) || (c && !r))
        """
        return True

    if requested_name is None or profile.name == INIT_TEMP_PROFILE_NAME:
        hash_ = util.hash256(json.dumps(profile))
        requested_name = f"default-{hash_[:16]}"

    try:
        controller = Profile.controller()

        # Erase any potential existing profile
        if controller.one({"name": requested_name}):
            controller.delete({"name": requested_name})

        controller.update({'name': requested_name}, profile.eid)
    except (UniqueAttributeError, ModelError) as err:
        LOGGER.error('Failed to rename profile: %s', err)
        return False

    return True


class InitCommand(AbstractCommand):
    """`init` macrocommand."""

    def _construct_parser(self):
        parser = get_parser(prog=self.command, description=self.summary)

        parser.add_argument(
            '--system',
            help="Initialize e4s-cl for use on a specific system."
            f" Available systems: {', '.join(builtin_profiles().keys())}" \
                    if builtin_profiles().keys() else \
                    "Initialize e4s-cl for use on a specific system."
                    " Use 'make install E4SCL_TARGETSYSTEM=<system>' to make "
                    " the associated profile available.",
            metavar='machine',
            default=SUPPRESS,
            choices=builtin_profiles().keys())

        parser.add_argument(
            '--launcher',
            help="MPI launcher required to run a sample program.",
            metavar='launcher',
            type=binary_in_path,
            default=SUPPRESS,
            dest='launcher',
        )

        parser.add_argument(
            '--launcher_args',
            help="MPI launcher arguments required to run a sample program.",
            metavar='launcher_args',
            default=SUPPRESS,
            dest='launcher_args',
        )

        parser.add_argument(
            '--mpi',
            type=posix_path,
            help="Path of the MPI installation to use with this profile",
            default=SUPPRESS,
            metavar='/path/to/mpi',
        )

        parser.add_argument(
            '--source',
            help="Script to source before execution with this profile",
            metavar='script',
            default=SUPPRESS,
            dest='source',
        )

        parser.add_argument(
            '--image',
            help="Container image to use by default with this profile",
            metavar='/path/to/image',
            default=SUPPRESS,
            dest='image',
        )

        parser.add_argument(
            '--backend',
            help="Container backend to use by default with this profile."
            f" Available backends are: {', '.join(EXPOSED_BACKENDS)}",
            metavar='technology',
            default=SUPPRESS,
            dest='backend',
        )

        parser.add_argument(
            '--profile',
            help="Profile to create. This will erase an existing profile !",
            metavar='profile_name',
            default=SUPPRESS,
            dest='profile_name',
        )

        parser.add_argument(
            '--wi4mpi',
            help="Path to the install directory of WI4MPI",
            metavar='path',
            default=SUPPRESS,
            dest='wi4mpi',
        )

        parser.add_argument(
            'cmd',
            help="Path to the install directory of WI4MPI",
            metavar='command',
            default=SUPPRESS,
            nargs=REMAINDER,
        )

        return parser

    def main(self, argv):
        args = self._parse_args(argv)

        system_args = getattr(args, 'system', False)
        detect_args = (getattr(args, 'mpi', False)
                       or getattr(args, 'cmd', False)
                       or getattr(args, 'launcher', False)
                       or getattr(args, 'launcher_args', False))

        if system_args and detect_args:
            self.parser.error(
                "--system and --mpi / --launcher / --launcher_args options are mutually exclusive"
            )

        profile_data = _profile_from_args(args)

        if system_args:
            # If using the downloaded assets, they would be loaded above
            pass
        else:
            profile_data['name'] = INIT_TEMP_PROFILE_NAME

        controller = Profile.controller()

        # Erase any leftover temporary profiles
        controller.delete({"name": profile_data['name']})

        # Create and select a profile for use
        profile = controller.create(profile_data)
        controller.select(profile)

        status = EXIT_SUCCESS

        if not system_args and _skip_analysis(args):
            try:
                status = _analyze_binary(args)
            except KeyboardInterrupt:
                status = EXIT_FAILURE

        if status == EXIT_FAILURE:
            controller.delete(profile.eid)
            return status

        # Reload the profile created above in case it was modified by the analysis
        selected_profile = Profile.selected()

        # Check for MPI in the analysis' results
        profile_libraries = map(Path, selected_profile.get('libraries', []))
        profile_mpi_libraries = filter_mpi_libs(profile_libraries)
        mpi_install_dir = library_install_dir(profile_mpi_libraries)

        # Simplify the profile by removing files contained in the MPI
        # installation directory
        profile_files = map(Path, profile.get('files', []))
        filtered_files = filter(
            lambda x: not util.path_contains(mpi_install_dir, x),
            profile_files)
        new_files = list(map(str, {*filtered_files, mpi_install_dir}))

        # Update the profile
        controller = Profile.controller()
        controller.update(
            dict(files=new_files),
            selected_profile.eid,
        )

        requested_name = (getattr(args, 'profile_name', None)
                          or profile_mpi_name(profile_mpi_libraries))

        if requested_name == INIT_TEMP_PROFILE_NAME:
            LOGGER.error(
                "This name is reserved. Please use another name for your profile"
            )
            return EXIT_FAILURE

        if not _rename_profile(selected_profile, requested_name):
            return EXIT_FAILURE

        LOGGER.info("Created profile %s", controller.selected().get('name'))

        return EXIT_SUCCESS


SUMMARY = "Initialize %(prog)s with the accessible MPI library, and create a profile with the results."

COMMAND = InitCommand(__name__, summary_fmt=SUMMARY)
