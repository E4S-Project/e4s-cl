"""
Entrypoint to the CLI
"""

import os
import sys
import e4s_cl
from e4s_cl import cli, logger, util, E4S_CL_VERSION, E4S_CL_SCRIPT
from e4s_cl.variables import SlaveAction, DryRunAction
from e4s_cl.cli import UnknownCommandError, arguments
from e4s_cl.cli.command import AbstractCommand

LOGGER = logger.get_logger(__name__)

HELP_PAGE_FMT = """'%(command)s' page to be written."""


class MainCommand(AbstractCommand):
    """Main entry point to the command line interface."""
    def __init__(self):
        summary_parts = [
            util.color_text("E4S Container Launcher %s" % E4S_CL_VERSION,
                            'red',
                            attrs=['bold'])
        ]

        super().__init__(__name__,
                         summary_fmt=''.join(summary_parts),
                         help_page_fmt=HELP_PAGE_FMT)

        self.command = os.path.basename(E4S_CL_SCRIPT)

    def _construct_parser(self):
        usage = "%s [arguments] <subcommand> [options]" % self.command
        epilog_parts = [
            "",
            cli.commands_description(), "",
            "See `%(command)s help <subcommand>` for more information on a subcommand."
        ]
        epilog = '\n'.join(epilog_parts) % {
            'color_command': util.color_text(self.command, 'cyan'),
            'command': self.command
        }
        parser = arguments.get_parser(prog=self.command,
                                      usage=usage,
                                      description=self.summary,
                                      epilog=epilog)

        parser.add_argument('command',
                            help="See subcommand descriptions below",
                            choices=cli.commands_next(),
                            metavar='<subcommand>')

        parser.add_argument('options',
                            help="Options to be passed to <subcommand>",
                            metavar='[options]',
                            nargs=arguments.REMAINDER)

        parser.add_argument('-V',
                            '--version',
                            action='version',
                            version=e4s_cl.version_banner())

        group = parser.add_mutually_exclusive_group()

        group.add_argument('-v',
                           '--verbose',
                           help="show debugging messages",
                           const='DEBUG',
                           default=arguments.SUPPRESS,
                           action='store_const')

        group.add_argument('-q',
                           '--quiet',
                           help="suppress all output except error messages",
                           const='ERROR',
                           default=arguments.SUPPRESS,
                           action='store_const')

        parser.add_argument(
            '-d',
            '--dry-run',
            nargs=0,
            help="Do nothing, print out what would be done instead",
            action=DryRunAction)

        parser.add_argument('--slave',
                            nargs=0,
                            help=arguments.SUPPRESS,
                            action=SlaveAction)

        return parser

    def main(self, argv):
        """Program entry point.

        Args:
            argv (list): Command line arguments.

        Returns:
            int: Process return code: non-zero if a problem occurred, 0 otherwise
        """

        # Disable built-in error catching for this special case
        self.parser.exit_on_error = False

        try:
            args = self._parse_args(argv)
        except arguments.ArgumentError as err:
            # Debug is enabled below, so the following statement enables
            # it for this code block
            if {'-v', '--verbose'} & set(argv):
                logger.set_log_level('DEBUG')
            LOGGER.debug("Argument parsing errored out with '%s'" % argv)

            # Check for the presence of a e4s-cl command
            empty = not len(argv)
            command = set(argv) & set(cli.commands_next())

            # If the error is not related to the omission of subcommand
            if empty or command:
                # Snippet coming from Lib/argparse.py:1853
                err = sys.exc_info()[1]
                self.parser.error(str(err))

            # Disable error catching
            self.parser.exit_on_error = True

            # Get a list of valid option strings from the parser
            option_strings = util.flatten(
                map(lambda x: x.option_strings, self.parser.actions))

            # Insert `launch` after any valid option string for e4s-cl
            for arg in argv:
                if arg in option_strings:
                    continue
                argv.insert(argv.index(arg), 'launch')
                break

            LOGGER.debug("Parsing updated arguments '%s'" % argv)
            args = self._parse_args(argv)

        self.parser.exit_on_error = True

        cmd = args.command
        cmd_args = args.options

        log_level = getattr(args, 'verbose',
                            getattr(args, 'quiet', logger.LOG_LEVEL))
        logger.set_log_level(log_level)

        LOGGER.debug('Arguments: %s', args)
        LOGGER.debug('Verbosity level: %s', logger.LOG_LEVEL)

        # Try to execute as a command
        try:
            return cli.execute_command([cmd], cmd_args)
        except UnknownCommandError:
            pass

        # Not sure what to do at this point, so advise the user and exit
        LOGGER.info("Unknown command.  Calling `%s help %s` to get advice.",
                    E4S_CL_SCRIPT, cmd)

        return cli.execute_command(['help'], [cmd])


COMMAND = MainCommand()

if __name__ == '__main__':
    sys.exit(COMMAND.main(sys.argv[1:]))
