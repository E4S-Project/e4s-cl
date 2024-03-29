"""
Definition of the help command. Subject to change as it was mostly imported from taucmdr.
"""

import os
import mimetypes
from e4s_cl import EXIT_SUCCESS, E4S_CL_SCRIPT
from e4s_cl import logger, util, cli
from e4s_cl.cli import arguments, UnknownCommandError
from e4s_cl.cli.command import AbstractCommand

LOGGER = logger.get_logger(__name__)

_SCRIPT_CMD = os.path.basename(E4S_CL_SCRIPT)

_GENERIC_HELP = f"See '{_SCRIPT_CMD} --help' or raise an issue on Github for assistance"

_KNOWN_FILES = {}

def _fuzzy_index(dct, full_key):
    """Return d[key] where ((key in k) == true) or return d[None]."""
    for key in dct:
        if key and (key in full_key):
            return dct[key]
    return dct[None]


def _guess_filetype(filename):
    """Return a (filetype, encoding) tuple for a file."""
    mimetypes.init()
    filetype = mimetypes.guess_type(filename)
    if not filetype[0]:
        textchars = bytearray([7, 8, 9, 10, 12, 13, 27]) + bytearray(
            range(0x20, 0x100))
        with open(filename, encoding='utf-8') as fd:
            if fd.read(1024).translate(None, textchars):
                filetype = ('application/unknown', None)
            else:
                filetype = ('text/plain', None)
    return filetype


def _gen_parts(cmd_obj):
    parts = []

    if cmd_obj.help_page:
        parts.extend(
            ["", util.hline("Help: " + cmd_obj.command), cmd_obj.help_page])
    if cmd_obj.usage:
        parts.extend(
            ["", util.hline("Usage: " + cmd_obj.command), cmd_obj.usage])

    return parts


class HelpCommand(AbstractCommand):
    """``help`` subcommand."""
    @staticmethod
    def exit_with_help(name):
        """Show a subcommands help page and exit."""
        cmd_obj = cli.find_command(name)
        util.page_output('\n'.join(_gen_parts(cmd_obj)))
        return EXIT_SUCCESS

    @staticmethod
    def exit_with_fullhelp():
        """Show a recursive help page for all commands and exit."""
        help_output = ''
        for cmd_name in cli.get_all_commands():
            name = cli.command_from_module_name(cmd_name)
            cmd_obj = cli.find_command(name.split()[1:])
            help_output += '\n'.join(_gen_parts(cmd_obj))
        util.page_output(help_output)
        return EXIT_SUCCESS

    def _construct_parser(self):
        usage_head = f"{self.command} <command>|<file>|all [arguments]"
        parser = arguments.get_parser(prog=self.command,
                                      usage=usage_head,
                                      description=self.summary)
        parser.add_argument('command',
                            help="An E4S command, system command, or file.",
                            metavar='(<command>|<file>|all)',
                            nargs='+')
        return parser

    def main(self, argv):
        args = self._parse_args(argv)
        if not args.command:
            return self.exit_with_help([])
        if args.command[0] == 'all':
            return self.exit_with_fullhelp()

        # Try to look up a e4s-cl command's built-in help page
        cmd = args.command
        try:
            return self.exit_with_help(cmd)
        except ImportError:
            pass

        # Is this a file?
        if os.path.exists(cmd):
            # Do we recognize the file name?
            try:
                desc, hint = _fuzzy_index(_KNOWN_FILES, cmd.lower())
            except KeyError:
                pass
            else:
                article = 'an' if desc[0] in 'aeiou' else 'a'
                hint = f"'{cmd}' is {article} {desc}.\n{hint}."
                raise UnknownCommandError(cmd, hint)

            # Get the filetype and try to be helpful.
            filetype, encoding = _guess_filetype(cmd)
            self.logger.debug("'%s' has filetype (%s, %s)", cmd, filetype,
                              encoding)
            raise UnknownCommandError(cmd)

        LOGGER.error("Cannot identify '%s' as a command or filename.", cmd)
        return self.exit_with_help('__main__')


COMMAND = HelpCommand(
    __name__,
    summary_fmt="Show help for a command or suggest actions for a file.")
