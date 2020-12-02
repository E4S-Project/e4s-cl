"""
Init command

Collection os scripts to setup a default profile and populate it
"""

import os
import json
import tempfile
import subprocess
import pathlib
from e4s_cl import EXIT_SUCCESS, E4S_CL_SCRIPT
from e4s_cl import logger, util
from e4s_cl.cli import arguments
from e4s_cl.cf.containers import guess_backend
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


class InitCommand(AbstractCommand):
    """`init` macrocommand."""
    def _construct_parser(self):
        usage = "%s <image>" % self.command
        parser = arguments.get_parser(prog=self.command,
                                      usage=usage,
                                      description=self.summary)
        parser.add_argument('--mpi',
                            type=arguments.posix_path,
                            help="Path of the MPI library to use",
                            default=arguments.SUPPRESS,
                            metavar='mpi')

        parser.add_argument('--source',
                            help="Script to source before execution",
                            metavar='script',
                            default=arguments.SUPPRESS,
                            dest='source')

        parser.add_argument('--image',
                            help="Container image to use by default",
                            metavar='path',
                            default=arguments.SUPPRESS,
                            dest='image')

        parser.add_argument('--backend',
                            help="Container backend to use by default",
                            metavar='technology',
                            default=arguments.SUPPRESS,
                            dest='backend')

        parser.add_argument('--launcher',
                            help="Launcher required to run the MPI program",
                            metavar='launcher',
                            default=arguments.SUPPRESS,
                            dest='launcher')

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

        if getattr(args, 'launcher', None):
            launcher = util.which(args.launcher)

        LOGGER.debug("Using MPI programs:\nCompiler: %s\nLauncher %s",
                     compiler, launcher)
        compile_sample(compiler, program.name)

        self.create_profile(args, {'compiler': compiler, 'launcher': launcher})

        arguments = [launcher, program.name]
        detect_command.main(arguments)

        return EXIT_SUCCESS


COMMAND = InitCommand(__name__, summary_fmt="Create defaults")
