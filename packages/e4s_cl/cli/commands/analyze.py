import os
from e4s_cl import EXIT_SUCCESS, E4S_CL_SCRIPT
from e4s_cl import logger
from e4s_cl.util import json_dumps
from e4s_cl.cli import arguments
from e4s_cl.cli.command import AbstractCommand
from e4s_cl.cf.libraries import libc_version, LibrarySet, resolve, GuestLibrary
from e4s_cl.model.profile import Profile

LOGGER = logger.get_logger(__name__)
_SCRIPT_CMD = os.path.basename(E4S_CL_SCRIPT)


class AnalyzeCommand(AbstractCommand):
    def _construct_parser(self):
        usage = "%s" % self.command
        parser = arguments.get_parser(prog=self.command,
                                      usage=usage,
                                      description=self.summary)
        parser.add_argument('--libraries',
                            help="Sonames to resolve and analyze",
                            nargs='+',
                            default=[],
                            metavar='soname')
        return parser

    def main(self, argv):
        args = self._parse_args(argv)

        cache = LibrarySet()
        for soname in args.libraries:
            path = resolve(soname, rpath=cache.rpath, runpath=cache.runpath)

            if not path:
                continue

            with open(path, 'rb') as file:
                cache.add(GuestLibrary(file))

        print(json_dumps(cache), end='')

        return EXIT_SUCCESS


COMMAND = AnalyzeCommand(__name__, summary_fmt="internal command")
