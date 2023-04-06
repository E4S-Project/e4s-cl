"""
This command is intended to be run once for any given MPI library, and will \
create a :ref:`profile<profile>` to substitute that library in a container.

This is done by tracing the execution of a program using a given MPI library. The opened files and libraries will be detected, filtered, and stored in a profile.

It is highly encouraged to load the MPI library beforehand using the module \
system available (:code:`spack`/:code:`modules`/:code:`lmod`) to ensure the \
paths and dependencies are valid and loaded.

A :ref:`profile<profile>` name will be generated from the version of the found MPI library. Make sure it corresponds to the library you want to use, or continue to the below section.

Changing launcher and libraries
*********************************

**e4s-cl** can load an MPI library and run it without any other information. This is however a very generic operation that may fail on your system. The following options can be used to tune this process:

--mpi
    MPI installation to target. **e4s-cl** will search for a launcher and libraries in this folder. If not supplied, the environment is used.

--launcher
    MPI launcher to use. Defaults to :code:`mpirun`.

--launcher_args
    Options to pass to the MPI launcher. Defaults to the empty string.

Alternatively, you can override the above options by providing a full command to run. This will require to compile an executable beforehand.

.. admonition:: The importance of inter-process communication

    This process relies on the execution of a sample MPI program to discover \
    its dependencies. In rare cases, a library will lazy-load network \
    libraries, preventing them from being detected with a simple example. \
    A message will appear in case some limitations were detected.

Examples
--------

Initializing using MPI resources from the environment:

.. code::

    module load mpich
    e4s-cl init  # Will use the launcher and library from the mpich module

Using :code:`srun` with special arguments:

.. code::

    module load cray-mpich-abi
    e4s-cl init --launcher srun
            --launcher_args "-A account-name -n 2 -N 2 -t 00:00:30"

Using a library installed on the system in :code:`/packages`:

.. code::

    e4s-cl init --mpi /packages/mpich --profile mpich

Using a fully formed command and an existing executable:

.. code-block:: bash

    $ e4s-cl init srun -n X -N Y ./executable

"""

import os
import json
import subprocess
import shlex
import argparse
from pathlib import Path
from typing import (
    List,
    Optional,
    Union,
)
from e4s_cl import (
    E4S_CL_MPI_TESTER_SCRIPT_NAME,
    E4S_CL_SCRIPT,
    EXIT_FAILURE,
    EXIT_SUCCESS,
    INIT_TEMP_PROFILE_NAME,
)
from e4s_cl import logger, util
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

LOGGER = logger.get_logger(__name__)
_SCRIPT_CMD = os.path.basename(E4S_CL_SCRIPT)


def _check_mpirun(executable: Union[str, Path]):
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


def _profile_from_args(args: argparse.Namespace) -> dict:
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

    return data


def _analyze_binary(args: argparse.Namespace) -> int:
    """
    Trace a command to determine the dynamic dependencies of the MPI library
    """

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


def _generate_command(args: argparse.Namespace) -> List[str]:
    """
    Generate a command from the given args with a launcher and mpi binary
    """
    # Use the environment's MPI scripts by default
    launcher = util.which('mpirun')

    # If an installation dir is specified, use its contents
    if getattr(args, 'mpi', None):
        mpirun = Path(args.mpi) / "bin" / "mpirun"
        if mpirun.exists():
            launcher = mpirun.as_posix()

        # Update LD_LIBRARY_PATH if provided path exist
        mpi_lib_dir = Path(args.mpi) / "lib"
        if mpi_lib_dir.exists():
            util.prepend_library_path(mpi_lib_dir)

    # Use the launcher and passed as an argument in priority
    launcher = getattr(args, 'launcher', launcher)
    launcher_args = shlex.split(getattr(args, 'launcher_args', ''))

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
    LOGGER.info("Tracing MPI execution using:\n'%s'", " ".join(command))

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
        # match (requested_name, current_name) with:
        #     (None, None) -> rename (create hash)
        #     (None, x) -> pass (keep x)
        #     (x, None) -> rename (set x)
        #     (x, y) -> rename (overwrite y with x)
        #     (x, x) -> pass

        # ==> Rename if !((r == c && r != None) || (c && !r))
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

    def _construct_parser(self) -> argparse.ArgumentParser:
        parser = get_parser(prog=self.command, description=self.summary)

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
            help="Name of the profile to create. This will erase an existing"
            " profile with the same name !",
            metavar='profile_name',
            default=SUPPRESS,
            dest='profile_name',
        )

        parser.add_argument(
            '--wi4mpi',
            help=
            "Path to the Wi4MPI install directory to use with this profile",
            metavar='path',
            default=SUPPRESS,
            dest='wi4mpi',
        )

        parser.add_argument(
            'cmd',
            help="Custom command to analyze, instead of the default. Use this"
            " if your MPI implementation has specificities set at compile time",
            metavar='command',
            default=SUPPRESS,
            nargs=REMAINDER,
        )

        return parser

    def main(self, argv: List[str]) -> int:
        args = self._parse_args(argv)

        profile_data = {'name': INIT_TEMP_PROFILE_NAME}

        controller = Profile.controller()

        # Erase any leftover temporary profiles
        controller.delete({"name": profile_data['name']})

        # Create and select a profile for use
        profile = controller.create(profile_data)
        controller.select(profile)

        status = EXIT_SUCCESS

        if _skip_analysis(args):
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
            {'files': new_files},
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
