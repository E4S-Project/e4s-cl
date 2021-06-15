"""
This command initializes E4S Container Launcher for the system's available MPI library.

During initialization, the available MPI library is parsed and analyzed to guess its running requirements.
A :ref:`profile<profile>` is created with the collected results from the analysis, and made accessible for the next :ref:`launch command<launch>`.

.. caution::

   The process relies on the good configuration of the MPI launcher, but this may fail.
   A message will appear in case some limitations were detected.
   It is good practice to :ref:`perform this process manually<init_override>` to ensure the network stack is exposed to **e4s-cl**.
"""

import os
import json
import tempfile
import subprocess
import pathlib
from e4s_cl import EXIT_FAILURE, EXIT_SUCCESS, E4S_CL_SCRIPT
from e4s_cl import logger, util
from e4s_cl.cli import arguments
from e4s_cl.cf.containers import guess_backend, EXPOSED_BACKENDS
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

        compiler = util.which('mpicc')
        launcher = util.which('mpirun')
        with tempfile.NamedTemporaryFile('w+', delete=False) as program_file:
            file_name = program_file.name

        if getattr(args, 'mpi', None):
            mpicc = pathlib.Path(args.mpi) / "bin" / "mpicc"
            if mpicc.exists():
                compiler = mpicc.as_posix()
            mpirun = pathlib.Path(args.mpi) / "bin" / "mpirun"
            if mpirun.exists():
                launcher = mpirun.as_posix()

        if not (compiler and launcher):
            LOGGER.error(
                "No MPI detected in PATH. Please load a module or use `--mpi`"
                + " to specify the MPI installation to use.")
            return EXIT_FAILURE

        if getattr(args, 'launcher', None):
            launcher = util.which(args.launcher)

        LOGGER.debug("Using MPI:\nCompiler: %s\nLauncher %s", compiler,
                     launcher)
        check_mpirun(launcher)
        compile_sample(compiler, file_name)

        create_profile(args, {'compiler': compiler, 'launcher': launcher})

        detect_command.main([launcher, file_name])

        return EXIT_SUCCESS


SUMMARY = "Initialize %(prog)s with the accessible MPI library, and create a profile with the results."

COMMAND = InitCommand(__name__, summary_fmt=SUMMARY)
