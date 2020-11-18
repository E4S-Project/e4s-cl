"""
Cancel the selection of a profile
"""

from e4s_cl import EXIT_SUCCESS
from e4s_cl.cli import arguments
from e4s_cl.model.profile import Profile
from e4s_cl.cli.command import AbstractCommand


class ProfileUnselectCommand(AbstractCommand):
    """``profile unselect`` subcommand."""
    def _construct_parser(self):
        usage = "%s" % self.command
        parser = arguments.get_parser(prog=self.command,
                                      usage=usage,
                                      description=self.summary)
        parser.add_argument('profile',
                            nargs='?',
                            type=arguments.defined_object(Profile, 'name'),
                            help="Name of the profile to unselect",
                            default=Profile.selected().get('name', arguments.UNSELECTED),
                            metavar="profile_name")
        return parser

    def main(self, argv):
        args = self._parse_args(argv)

        if args.profile.get('name') != Profile.selected().get('name'):
                self.parser.error("Profile {} is not selected.".format(
                    args.profile.get('name')))

        Profile.controller().unselect()
        return EXIT_SUCCESS


COMMAND = ProfileUnselectCommand(
    __name__,
    summary_fmt=("Unselect the selected profile.\n"
                 "Use `profile list` to see all profiles."))
