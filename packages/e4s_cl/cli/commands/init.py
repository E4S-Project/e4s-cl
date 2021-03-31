"""
Init command

Collection os scripts to setup a default profile and populate it
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
from e4s_cl.sample import program
from e4s_cl.cli.command import AbstractCommand
from e4s_cl.cli.commands.profile.detect import COMMAND as detect_command
from e4s_cl.model.profile import Profile

LOGGER = logger.get_logger(__name__)
_SCRIPT_CMD = os.path.basename(E4S_CL_SCRIPT)


def compile_sample(compiler, destination):
    std_in = tempfile.TemporaryFile('w+')
    std_in.write(program)
    std_in.seek(0)

    command = "%s -o %s -lm -x c -" % (compiler, destination)
    subprocess.Popen(command.split(), stdin=std_in).wait()


def check_mpirun(executable):
    proc = subprocess.Popen([executable, 'hostname'], stdout=subprocess.PIPE)
    proc.wait()

    hostnames = {hostname.strip() for hostname in proc.stdout.readlines()}

    if len(hostnames) == 1:
        LOGGER.warn(
            "The target launcher %s uses a single host by default, "
            "which may tamper with the library discovery. Consider "
            "running `%s` using mpirun specifying multiple hosts.", executable,
            str(detect_command))


class InitCommand(AbstractCommand):
    """`init` macrocommand."""
    def _construct_parser(self):
        usage = "%s <image>" % self.command
        parser = arguments.get_parser(prog=self.command,
                                      usage=usage,
                                      description=self.summary)
        parser.add_argument('--launcher',
                            help="Launcher required to run the MPI analysis",
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

        return parser

    def create_profile(self, args, metadata):
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

        self.profile_hash = "default-%s" % util.hash256(json.dumps(metadata))

        if controller.one({"name": self.profile_hash}):
            controller.delete({"name": self.profile_hash})

        data["name"] = self.profile_hash
        profile = controller.create(data)

        controller.select(profile)

    def main(self, argv):
        args = self._parse_args(argv)

        compiler = util.which('mpicc')
        launcher = util.which('mpirun')
        program = tempfile.NamedTemporaryFile('w+', delete=False)
        program.close()

        if getattr(args, 'mpi', None):
            mpicc = pathlib.Path(args.mpi) / "bin" / "mpicc"
            if mpicc.exists():
                compiler = mpicc.as_posix()
            mpirun = pathlib.Path(args.mpi) / "bin" / "mpirun"
            if mpirun.exists():
                launcher = mpirun.as_posix()

        if not (compiler and launcher):
            LOGGER.error(
                "No MPI detected in PATH. Please load a module or " +
                "use `--mpi` to specify the MPI installation to use.")
            return EXIT_FAILURE

        if getattr(args, 'launcher', None):
            launcher = util.which(args.launcher)

        LOGGER.debug("Using MPI programs:\nCompiler: %s\nLauncher %s",
                     compiler, launcher)
        check_mpirun(launcher)
        compile_sample(compiler, program.name)

        self.create_profile(args, {'compiler': compiler, 'launcher': launcher})

        arguments = [launcher, program.name]
        detect_command.main(arguments)

        return EXIT_SUCCESS

SUMMARY="""
Initialize %(prog)s. This helper will analyze the accessible MPI library, and create a profile with the results.
"""

COMMAND = InitCommand(__name__, summary_fmt=SUMMARY)
