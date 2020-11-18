"""
Show a profile's configuration in detail.
"""

from e4s_cl import EXIT_SUCCESS
from e4s_cl.cli import arguments
from e4s_cl.cli.cli_view import ShowCommand
from e4s_cl.model.profile import Profile

class ShowProfileCommand(ShowCommand):
    def _construct_parser(self):
        usage = ("%(command)s [arguments] <%(model_name)s_%(key_attr)s>" %
                 self._format_fields)

        parser = arguments.get_parser(prog=self.command,
                                      usage=usage,
                                      description=self.summary)

        parser.add_argument('profile',
                            nargs='?',
                            type=arguments.defined_object(Profile, 'name'),
                            help="Name of the profile to show",
                            default=Profile.selected().get('name', arguments.UNSELECTED),
                            metavar="%(model_name)s_%(key_attr)s" % self._format_fields)
        return parser

    def main(self, argv):
        self.detail(self._parse_args(argv).profile)

        return EXIT_SUCCESS

COMMAND = ShowProfileCommand(Profile, __name__)
