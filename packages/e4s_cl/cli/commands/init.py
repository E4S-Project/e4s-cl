"""
Init command

Collection os scripts to setup a default profile and populate it
"""

import os
import tempfile
import subprocess
from argparse import ArgumentTypeError, Namespace
from e4s_cl import EXIT_SUCCESS, E4S_CL_SCRIPT
from e4s_cl import logger, util
from e4s_cl.cli import arguments
from e4s_cl.sample import program
from e4s_cl.cli.command import AbstractCommand
from e4s_cl.model.profile import Profile

LOGGER = logger.get_logger(__name__)
_SCRIPT_CMD = os.path.basename(E4S_CL_SCRIPT)


def compile_sample():
    std_in = tempfile.TemporaryFile('w+')
    std_in.write(program)
    std_in.seek(0)

    mpicc = util.which('mpicc')
    LOGGER.debug("Compiling with %s" % mpicc)

    command = "%s -o sample -lm -x c -" % mpicc
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
        parser.add_argument('image',
                            help="Container image to use",
                            metavar='image',
                            nargs=arguments.REMAINDER)
        return parser

    def main(self, argv):
        args = self._parse_args(argv)

        compile_sample()

        return EXIT_SUCCESS


COMMAND = InitCommand(__name__, summary_fmt="Create defaults")
