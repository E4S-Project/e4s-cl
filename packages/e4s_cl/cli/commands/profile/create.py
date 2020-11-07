"""
Create a profile from CLI arguments
"""

from e4s_cl.cli import arguments
from e4s_cl.cli.cli_view import CreateCommand
from e4s_cl.model.profile import Profile


class ProfileCreateCommand(CreateCommand):
    """``profile create`` subcommand."""
    def _construct_parser(self):
        usage = "%s <profile_name>" % self.command
        parser = arguments.get_parser_from_model(self.model,
                                                 prog=self.command,
                                                 usage=usage,
                                                 description=self.summary)
        parser.add_argument('--libraries',
                            help="Library configurations in this profile",
                            metavar='l',
                            nargs='+',
                            type=arguments.posix_path,
                            default=arguments.SUPPRESS,
                            dest='libraries')

        parser.add_argument('--files',
                            help="Files configurations in this profile",
                            metavar='f',
                            nargs='+',
                            type=arguments.posix_path,
                            default=arguments.SUPPRESS,
                            dest='files')

        parser.add_argument('--backend',
                            help="Container backend for this profile",
                            metavar='b',
                            default=arguments.SUPPRESS,
                            dest='backend')

        parser.add_argument('--image',
                            help="Container image for this profile",
                            metavar='i',
                            default=arguments.SUPPRESS,
                            dest='image')

        parser.add_argument('--source',
                            help="Script to source before running the program",
                            metavar='script',
                            default=arguments.SUPPRESS,
                            dest='source')

        return parser


COMMAND = ProfileCreateCommand(Profile, __name__)
