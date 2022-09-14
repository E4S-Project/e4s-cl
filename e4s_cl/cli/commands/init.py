"""
This command is intended to be run once, and will create a \
:ref:`profile<profile>` from the resources made available to it. \
Initialization can be achieved in one of three ways, depending on the \
arguments passed to the command.

In case no method is explicitly invoked, the fallback in the MPI library \
analysis, by using the MPI compiler and launcher available in the environment.

Using the system name
-----------------------

If the current system is supported, use the :code:`--system` argument to \
flag its use. The available values are listed when using \
:code:`e4s-cl init -h`. In order to have the system-specific profiles \
available (and listed as available), the \
:code:`E4SCL_TARGETSYSTEM=<system>` flag needs to be used when installing \
the project.

Using a WI4MPI installation
----------------------------

If an WI4MPI installation is present on the system, one can link a profile \
to it using the :code:`--wi4mpi` and :code:`--wi4mpi_options` arguments. The \
profile will contain this information and the installation will be used \
during launch.

Using an installed MPI library
--------------------------------

This initialization method will create a profile from the execution analysis \
of a sample MPI program. A program compiled with the MPI library's compiler \
will run using a provided launcher. The opened files and libraries will be \
detected using the :code:`ptrace` system call, and added to the resulting \
profile.

The :code:`--mpi`, :code:`--launcher` and :code:`--launcher_args` options can \
be used to influence the initialization process. It is highly encouraged to \
load the MPI library beforehand using the module system available \
(:code:`spack`/:code:`modules`/:code:`lmod`) to ensure the paths and \
dependencies are valid and loaded as well.

.. admonition:: The importance of inter-process communication

    This process relies on the execution of a sample MPI program to discover \
    its dependencies. In some cases, a library will lazy-load network \
    libraries, preventing them from being detected. A message will appear in \
    case some limitations were detected.

    In case of error, it is good practice to perform this process \
    :ref:`manually<init_override>` to ensure the network stack is used and \
    exposed to **e4s-cl**.

If no :ref:`profile<profile>` name is passed to :code:`--profile`, a profile \
name will be generated from the version of the found MPI library.

Examples
--------

Initializing using the available MPI resources:

.. code::

    module load mpich
    e4s-cl init --profile mpich

Using a library installed on the system in :code:`/packages`:

.. code::

    e4s-cl init --mpi /packages/mpich --profile mpich

Using an installation of WI4MPI:

.. code::

    e4s-cl init --wi4mpi /packages/wi4mpi \\
            --wi4mpi_options \\
            "-T openmpi -F mpich"
"""

import os
import json
import tempfile
import subprocess
import shlex
from argparse import ArgumentTypeError
from pathlib import Path
from sotools.linker import resolve
from e4s_cl import EXIT_FAILURE, EXIT_SUCCESS, E4S_CL_SCRIPT, INIT_TEMP_PROFILE_NAME
from e4s_cl import logger, util
from e4s_cl.cf.assets import precompiled_binaries, builtin_profiles
from e4s_cl.cf.detect_name import rename_profile_mpi_version
from e4s_cl.cf.wi4mpi.install import check_wi4mpi, WI4MPI_DIR
from e4s_cl.cf.containers import guess_backend, EXPOSED_BACKENDS
from e4s_cl.cli import arguments
from e4s_cl.cli.command import AbstractCommand
from e4s_cl.cli.commands.profile.detect import COMMAND as detect_command
from e4s_cl.error import UniqueAttributeError
from e4s_cl.model.profile import Profile
from e4s_cl.sample import PROGRAM

LOGGER = logger.get_logger(__name__)
_SCRIPT_CMD = os.path.basename(E4S_CL_SCRIPT)


def _compile_sample(compiler) -> Path:
    """
    Compile a sample MPI program that can be used with the profile detect command
    """
    # Create a file to compile a sample program in
    with tempfile.NamedTemporaryFile('w+', delete=False) as binary:
        with tempfile.NamedTemporaryFile('w+', suffix='.c') as program:
            program.write(PROGRAM)
            program.seek(0)

            command = "%(compiler)s -o %(output)s -lm %(code)s" % {
                'compiler': compiler,
                'output': binary.name,
                'code': program.name,
            }

            LOGGER.debug("Compiling with: '%s'", command)
            with subprocess.Popen(command.split()) as compilation:
                compilation_status = compilation.wait()

    # Check for a non-zero return code
    if compilation_status:
        LOGGER.error(
            "Failed to compile sample MPI program with the following compiler: %s",
            compiler)
        return None

    return binary.name


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

    for attr in ['image', 'backend', 'source', 'wi4mpi', 'wi4mpi_options']:
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


def _select_binary(binary_dict):
    # Selects an available mpi vendor
    for libso in binary_dict.keys():
        if resolve(libso) is not None:
            return str(binary_dict[libso])
    LOGGER.debug(
        "MPI vendor not supported by precompiled binary initialisation\n"
        "Proceeding with legacy initialisation")
    return None


def _analyze_binary(args):
    # If no profile has been loaded or wi4mpi is not used, then
    # we need to analyze a binary to
    # determine the dynamic dependencies of the library

    # Use the MPI environment scripts by default
    compiler = util.which('mpicc')
    launcher = util.which('mpirun')

    # If a library is specified, get the executables
    if getattr(args, 'mpi', None):
        mpicc = Path(args.mpi) / "bin" / "mpicc"
        if mpicc.exists():
            compiler = mpicc.as_posix()

        mpirun = Path(args.mpi) / "bin" / "mpirun"
        if mpirun.exists():
            launcher = mpirun.as_posix()

        # Update LD_LIBRARY_PATH if provided path exist
        mpi_lib = Path(args.mpi) / "lib"
        if mpi_lib.exists():
            os.environ["LD_LIBRARY_PATH"] = mpi_lib.as_posix()

    # Select binary depending on available library
    binary = _select_binary(precompiled_binaries())

    # Use the launcher passed as an argument in priority
    arg_launcher = getattr(args, 'launcher', None)
    if arg_launcher:
        launcher = arg_launcher

    launcher_args = shlex.split(getattr(args, 'launcher_args', ''))

    # If no binary, check for compiler and compile a binary
    if not binary:
        if not compiler:
            LOGGER.error(
                "No MPI compiler detected. Please load a module or "
                "use the `--mpi` option to specify the MPI installation to use."
            )
            return EXIT_FAILURE
        binary = _compile_sample(compiler)

        # Exit now if we failed producing a compatible binary
        if not binary:
            return EXIT_FAILURE

    # Check for launcher and then launch the detect command
    if not launcher:
        LOGGER.error(
            "No launcher detected. Please load a module, use the `--mpi` "
            "or `--launcher` options to specify the launcher program to use.")
        return EXIT_FAILURE

    LOGGER.warning("Tracing MPI execution using:\nCompiler: %s\nLauncher %s",
                   compiler, " ".join([launcher, *launcher_args]))

    # If no arguments were given, check the default behaviour of the launcher
    if not launcher_args:
        _check_mpirun(launcher)

    # Run the program using the detect command and get a file list
    returncode = detect_command.main([launcher, *launcher_args, binary])

    if returncode != EXIT_SUCCESS:
        LOGGER.error("Tracing of MPI execution failed")
        return EXIT_FAILURE

    return EXIT_SUCCESS


def _skip_analysis(args) -> bool:
    """
    Skip analysis step when certain conditions are met
    """

    # If using shifter, do not try to profile a library
    if getattr(args, 'backend', '') == 'shifter':
        return False

    if getattr(args, 'wi4mpi', ''):
        return False

    return True


def launcher_argument(string):
    """ Argument type callback. Asserts the given string identifies a launcher binary
    on the system. """

    path = util.which(string)
    if not path:
        raise ArgumentTypeError(
            f"Launcher argument '{string}' could not be resolved to a binary")
    return path


def _rename_hash_or_delete(profile):
    """Rename the given profile to a hash of its own contents, or delete
    it if a similar profile already exists"""
    controller = Profile.controller()
    hash_ = util.hash256(json.dumps(profile))
    try:
        controller.update({'name': f"default-{hash_[:16]}"}, profile.eid)
    except UniqueAttributeError:
        LOGGER.debug('Profile already exists, deleting temporary profile')
        controller.delete(profile.eid)


class InitCommand(AbstractCommand):
    """`init` macrocommand."""

    def _construct_parser(self):
        parser = arguments.get_parser(prog=self.command,
                                      description=self.summary)

        parser.add_argument(
            '--system',
            help="Initialize e4s-cl for use on a specific system."
            f" Available systems: {', '.join(builtin_profiles().keys())}" \
                    if builtin_profiles().keys() else \
                    "Initialize e4s-cl for use on a specific system."
                    " Use 'make install E4SCL_TARGETSYSTEM=<system>' to make "
                    " the associated profile available.",
            metavar='machine',
            default=arguments.SUPPRESS,
            choices=builtin_profiles().keys())

        parser.add_argument(
            '--launcher',
            help="MPI launcher required to run a sample program.",
            metavar='launcher',
            type=launcher_argument,
            default=arguments.SUPPRESS,
            dest='launcher')

        parser.add_argument(
            '--launcher_args',
            help="MPI launcher arguments required to run a sample program.",
            metavar='launcher_args',
            default=arguments.SUPPRESS,
            dest='launcher_args')

        parser.add_argument(
            '--mpi',
            type=arguments.posix_path,
            help="Path of the MPI installation to use with this profile",
            default=arguments.SUPPRESS,
            metavar='/path/to/mpi')

        parser.add_argument(
            '--source',
            help="Script to source before execution with this profile",
            metavar='script',
            default=arguments.SUPPRESS,
            dest='source')

        parser.add_argument(
            '--image',
            help="Container image to use by default with this profile",
            metavar='/path/to/image',
            default=arguments.SUPPRESS,
            dest='image')

        parser.add_argument(
            '--backend',
            help="Container backend to use by default with this profile."
            f" Available backends are: {', '.join(EXPOSED_BACKENDS)}",
            metavar='technology',
            default=arguments.SUPPRESS,
            dest='backend')

        parser.add_argument(
            '--profile',
            help="Profile to create. This will erase an existing profile !",
            metavar='profile_name',
            default=arguments.SUPPRESS,
            dest='profile_name')

        parser.add_argument('--wi4mpi',
                            help="Path to the install directory of WI4MPI",
                            metavar='path',
                            default=arguments.SUPPRESS,
                            dest='wi4mpi')

        parser.add_argument('--wi4mpi_options',
                            help="Options to use with WI4MPI",
                            metavar='opts',
                            default=arguments.SUPPRESS,
                            dest='wi4mpi_options')

        return parser

    def main(self, argv):
        args = self._parse_args(argv)

        system_args = getattr(args, 'system', False)
        wi4mpi_args = getattr(args, 'wi4mpi', False) or getattr(
            args, 'wi4mpi_options', False)
        detect_args = getattr(args, 'mpi', False) or getattr(
            args, 'launcher', False) or getattr(args, 'launcher_args', False)

        if system_args and wi4mpi_args:
            self.parser.error(
                "--system and --wi4mpi options are mutually exclusive")
        if system_args and detect_args:
            self.parser.error(
                "--system and --mpi / --launcher / --launcher_args options are mutually exclusive"
            )
        if detect_args and wi4mpi_args:
            self.parser.error(
                "--wi4mpi and --mpi / --launcher / --launcher_args options are mutually exclusive"
            )

        profile_data = _profile_from_args(args)

        if system_args:
            # If using the downloaded assets, they would be loaded above
            pass
        elif wi4mpi_args:
            # If using wi4mpi, no need to profile a binary, as the installation
            # will details the required binaries
            profile_data['name'] = 'wi4mpi'
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
        requested_name = getattr(args, 'profile_name', None)

        # Determine if wi4mpi is needed depending on mpi version detected
        INSTALLED = check_wi4mpi(selected_profile)
        if INSTALLED:
            controller.update(
                {
                    'wi4mpi': str(WI4MPI_DIR / 'install'),
                    'wi4mpi_options': '-T mpich -F openmpi'
                }, profile.eid)

        # Rename the profile. This is done last to allow dynamic renaming
        if requested_name:
            # Rename the profile to the name passed as an argument
            # Erase any potential existing profile
            if controller.one({"name": requested_name}):
                controller.delete({"name": requested_name})
            # Rename the profile created and selected above
            controller.update({'name': requested_name}, profile.eid)
        elif selected_profile.get('name') == INIT_TEMP_PROFILE_NAME:
            mpi_renaming = rename_profile_mpi_version(selected_profile)
            # Renaming according to MPI failed, hash renaming instead
            if not mpi_renaming:
                _rename_hash_or_delete(selected_profile)

        return status


SUMMARY = "Initialize %(prog)s with the accessible MPI library, and create a profile with the results."

COMMAND = InitCommand(__name__, summary_fmt=SUMMARY)
