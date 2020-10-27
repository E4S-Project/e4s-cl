"""
Init command

Collection os scripts to setup a default profile and populate it
"""

import os
import json
import tempfile
import subprocess
import pathlib
from argparse import ArgumentTypeError, Namespace
from e4s_cl import EXIT_SUCCESS, E4S_CL_SCRIPT
from e4s_cl import logger, util
from e4s_cl.cli import arguments
from e4s_cl.sample import program
from e4s_cl.cli.command import AbstractCommand
from e4s_cl.model.profile import Profile

LOGGER = logger.get_logger(__name__)
_SCRIPT_CMD = os.path.basename(E4S_CL_SCRIPT)


def compile_sample(compiler):
    std_in = tempfile.TemporaryFile('w+')
    std_in.write(program)
    std_in.seek(0)

    command = "%s -o sample -lm -x c -" % compiler
    subprocess.Popen(command.split(), stdin=std_in)


class InitCommand(AbstractCommand):
    """`init` macrocommand."""
    def _construct_parser(self):
        usage = "%s <image>" % self.command
        parser = arguments.get_parser(prog=self.command,
                                      usage=usage,
                                      description=self.summary)
        parser.add_argument('--mpi',
                            type=arguments.posix_path,
                            help="Path to the mpi library to use",
                            default=arguments.SUPPRESS,
                            metavar='mpi')

        parser.add_argument('--image',
                            help="Container image to use by default",
                            metavar='i',
                            default=arguments.SUPPRESS,
                            dest='image')

        return parser

    def main(self, argv):
        args = self._parse_args(argv)

        compiler = None
        launcher = None

        if 'mpi' in dir(args):
            mpicc = pathlib.Path(args.mpi) / "bin" / "mpicc"
            if mpicc.exists():
                LOGGER.info("Found %s" % mpicc.as_posix())
                compiler = mpicc.as_posix()
        else:
            compiler = util.which('mpicc')
            launcher = util.which('mpirun')

        compile_sample(compiler)

        data = {}

        profile_hash = "default-%s" % util.hash256(json.dumps(data))

        profile = Profile.controller().one({"name": profile_hash})

        if not profile:
            data["name"] = profile_hash
            profile = Profile.controller().create(data)

        Profile.controller().select(profile)

        return EXIT_SUCCESS


COMMAND = InitCommand(__name__, summary_fmt="Create defaults")
