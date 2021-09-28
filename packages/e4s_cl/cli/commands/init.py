"""
This command initializes E4S Container Launcher for the system's available MPI \
library.

During initialization, the available MPI library is parsed and analyzed to \
guess its running requirements.
A :ref:`profile<profile>` is created with the collected results from the \
analysis, and made accessible for the next :ref:`launch command<launch>`.

If no :ref:`profile<profile>` name is passed to :code:`--profile`, a profile \
name will be generated from the parameters of the initialization.

.. admonition:: The importance of inter-process communication

    This process relies on the execution of a sample MPI program to discover \
its dependencies.
    In some cases, a library will lazy-load network libraries, preventing \
them from being detected.
    A message will appear in case some limitations were detected.

    In case of error, it is good practice to \
:ref:`perform this process manually<init_override>` to ensure the network \
stack is used and exposed to **e4s-cl**.

Examples
----------

Initializing using the available MPI resources:

.. code::

    module load mpich
    e4s-cl init --profile mpich

Using a library installed on the system in :code:`/packages`:

.. code::

    e4s-cl init --mpi /packages/mpich --profile mpich

"""

import re
import os
import json
import tempfile
import subprocess
import ctypes
from pathlib import Path
from e4s_cl import EXIT_FAILURE, EXIT_SUCCESS, E4S_CL_SCRIPT
from e4s_cl import logger, util
from e4s_cl.cli import arguments
from e4s_cl.cf.containers import guess_backend, EXPOSED_BACKENDS
from e4s_cl.cf.libraries import LibrarySet
from e4s_cl.sample import PROGRAM
from e4s_cl.cli.command import AbstractCommand
from e4s_cl.cli.commands.profile.detect import COMMAND as detect_command
from e4s_cl.model.profile import Profile

LOGGER = logger.get_logger(__name__)
_SCRIPT_CMD = os.path.basename(E4S_CL_SCRIPT)


def compile_sample(compiler, destination):
    command = "%s -o %s -lm -x c -" % (compiler, destination)

    with tempfile.TemporaryFile('w+') as std_in:
        std_in.write(PROGRAM)
        std_in.seek(0)

        subprocess.Popen(command.split(), stdin=std_in).wait()


def check_mpirun(executable):
    if not (hostname_bin := util.which('hostname')):
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


def detect_name(path_list):
    """
    Given a list of shared objects, get an MPI library name and version
    """
    profile_name, version_str = '', ''
    version_buffer = ctypes.create_string_buffer(3000)
    length = ctypes.c_int()

    distro_dict = {
        'Intel(R) MPI':
        (lambda x: x.split("Library", 1)[1].split("for", 1)[0]),
        'Open MPI': (lambda x: x.split("v", 1)[1].split(",", 1)[0]),
        'Spectrum MPI': (lambda x: x.split("v", 1)[1].split(",", 1)[0]),
        'MPICH': (lambda x: x.split(":", 1)[1].split("M", 1)[0]),
        'MVAPICH': (lambda x: x.split(":", 1)[1].split("M", 1)[0])
    }

    def _extract_vinfo(path: Path):
        # Get the a handle to the MPI_Get_library_version function given
        # a path to a shared object
        if not path.exists():
            return None

        try:
            handle = ctypes.CDLL(path)
            return getattr(handle, 'MPI_Get_library_version', None)
        except OSError as err:
            LOGGER.debug("Error loading shared object %s: %s", path.as_posix(),
                         str(err))
            return None

    # Handles found in the library list
    version_f = list(filter(None, map(_extract_vinfo, path_list)))
    # Container for the results
    version_data = set()  # Set((Str, Version))

    for f in version_f:
        # Run every handle
        f(version_buffer, ctypes.byref(length))

        if length:
            version_buffer_str = version_buffer.value.decode("utf-8")[:500]

            # Check for keywords in the buffer
            filtered_buffer = set(
                filter(lambda x: x in version_buffer_str, distro_dict.keys()))

            if len(filtered_buffer) != 1:
                # If we found multiple vendors => error
                continue

            profile_name = filtered_buffer.pop()
            # Run the corresponding function on the buffer
            version_str = "_" + distro_dict.get(
                profile_name, lambda x: None)(version_buffer_str)

            # Add the result to the above container
            version_data.add((profile_name, version_str))

    found_vendors = set(map(lambda x: x[0], version_data))

    if len(found_vendors) == 1:
        # If one consistent vendor has been found
        profile_name, version_str = version_data.pop()
        profile_name = profile_name + version_str
        profile_name = ''.join(profile_name.split())

    return profile_name

def create_profile(args, metadata):
    """Populate profile record"""
    data = {}

    controller = Profile.controller()

    if getattr(args, 'image', None):
        data['image'] = args.image

    if getattr(args, 'backend', None):
        data['backend'] = args.backend
    elif getattr(args, 'image', None) and guess_backend(args.image):
        data['backend'] = guess_backend(args.image)

    if getattr(args, 'source', None):
        data['source'] = args.source


    profile_name = getattr(args, 'profile_name',
                       "default-%s" % util.hash256(json.dumps(metadata)))

    if controller.one({"name": profile_name}):
        controller.delete({"name": profile_name})

    data["name"] = profile_name
    profile = controller.create(data)
    controller.select(profile)

def _suffix_profile(profile_name: str) -> str:
    """
    Add a '-N' to a profile if it already exists
    """
    escaped_profile_name = re.escape(profile_name)
    pattern = re.compile("%s.*" % escaped_profile_name)
    matches = Profile.controller().match('name', regex=pattern)
    names = set(filter(None, map(lambda x: x.get('name'), matches)))

    # Do not append a suffix for the first unique profile
    if not profile_name in names:
        return profile_name

    # An exact match exists, filter the occurences of 'name-N' (clones)
    # and return name-max(N)+1
    clones = set(
        filter(
            None,
            map(lambda x: re.match("%s-(?P<ordinal>[0-9]*)" % escaped_profile_name, x),
                names)))

    # Try to list all clones of this profile
    ordinals = []
    for clone in clones:
        try:
            ordinals.append(int(clone.group('ordinal')))
        except ValueError:
            pass

    # If there are no clones, this is the second profile, after the original
    profile_no = 2
    if len(ordinals):
        profile_no = max(ordinals) + 1

    return '%s-%d' % (profile_name, profile_no)


class InitCommand(AbstractCommand):
    """`init` macrocommand."""
    def _construct_parser(self):
        usage = "%s <image>" % self.command
        parser = arguments.get_parser(prog=self.command,
                                      usage=usage,
                                      description=self.summary)
        parser.add_argument(
            '--launcher',
            help="MPI launcher required to run a sample program.",
            metavar='launcher',
            default=arguments.SUPPRESS,
            dest='launcher')

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
            help="Container backend to use by default with this profile." +
            " Available backends are: %s" % ", ".join(EXPOSED_BACKENDS),
            metavar='technology',
            default=arguments.SUPPRESS,
            dest='backend')

        parser.add_argument(
            '--profile',
            help="Profile to create. This will erase an existing profile !",
            metavar='profile_name',
            default=arguments.SUPPRESS,
            dest='profile_name')

        return parser

    def main(self, argv):
        args = self._parse_args(argv)

        with tempfile.NamedTemporaryFile('w+', delete=False) as program_file:
            file_name = program_file.name

        # Use the environment compiler per default
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

        # Use the launcher passed as an argument in priority
        launcher = util.which(getattr(args, 'launcher', launcher))

        if not compiler:
            LOGGER.error(
                "No MPI compiler detected. Please load a module or use the `--mpi` option to specify the MPI installation to use."
            )
            return EXIT_FAILURE

        if not launcher:
            LOGGER.error(
                "No launcher detected. Please load a module, use the `--mpi` or `--launcher` options to specify the launcher program to use."
            )
            return EXIT_FAILURE

        LOGGER.debug("Using MPI:\nCompiler: %s\nLauncher %s", compiler,
                     launcher)
        check_mpirun(launcher)
        compile_sample(compiler, file_name)

        create_profile(args, {'compiler': compiler, 'launcher': launcher})

        returncode = detect_command.main([launcher, file_name])

        if returncode != EXIT_SUCCESS:
            LOGGER.error("Failed detecting libraries !")
            return EXIT_FAILURE

        detected_libs = LibrarySet.create_from(Profile.selected()['libraries'])

        mpi_libs = list(filter(lambda x: re.match(r'libmpi.*so.*', x.soname), detected_libs))

        if profile_name := detect_name([Path(x.binary_path) for x in mpi_libs]):
            profile_name = _suffix_profile(profile_name)
            Profile.controller().update({'name': profile_name}, Profile.selected().eid)

        return EXIT_SUCCESS


SUMMARY = "Initialize %(prog)s with the accessible MPI library, and create a profile with the results."

COMMAND = InitCommand(__name__, summary_fmt=SUMMARY)
