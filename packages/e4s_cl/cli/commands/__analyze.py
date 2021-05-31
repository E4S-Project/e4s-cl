"""
Command run in containers to get information
This command is used internally and thus cloaked from the UI
"""

import os
from e4s_cl import EXIT_SUCCESS, E4S_CL_SCRIPT
from e4s_cl import logger
from e4s_cl.util import json_dumps
from e4s_cl.cli import arguments
from e4s_cl.cli.command import AbstractCommand
from e4s_cl.cf import pipe
from e4s_cl.cf.libraries import libc_version, LibrarySet, resolve, GuestLibrary

LOGGER = logger.get_logger(__name__)
_SCRIPT_CMD = os.path.basename(E4S_CL_SCRIPT)


class AnalyzeCommand(AbstractCommand):
    """
    Analysis command. This command is intended to be ran inside of an
    environment to analyze (e.g. a container), and will resolve and parse
    shared objects from the inside to ensure the validity the resulting
    composite environment.
    """
    def _construct_parser(self):
        usage = "%s" % self.command
        parser = arguments.get_parser(prog=self.command,
                                      usage=usage,
                                      description=self.summary)

        parser.add_argument('--libraries',
                            help="Sonames to resolve and analyze",
                            nargs='*',
                            default=[],
                            metavar='soname')

        return parser

    def main(self, argv):
        args = self._parse_args(argv)

        fd = pipe.attach()

        guest_libraries = LibrarySet()

        for soname in args.libraries:
            path = resolve(soname,
                           rpath=guest_libraries.rpath,
                           runpath=guest_libraries.runpath)

            if not path:
                continue

            with open(path, 'rb') as file:
                guest_libraries.add(GuestLibrary(file))

        data = {
            'libc_version': str(libc_version()),
            'libraries': guest_libraries,
        }

        os.write(fd, json_dumps(data).encode('utf-8'))

        return EXIT_SUCCESS


COMMAND = AnalyzeCommand(__name__, summary_fmt="internal command")
