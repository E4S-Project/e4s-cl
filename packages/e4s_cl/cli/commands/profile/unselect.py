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
        parser = arguments.get_model_identifier(Profile,
                                                prog=self.command,
                                                usage=usage,
                                                description=self.summary)
        return parser

    def main(self, argv):
        profile_name = self._parse_args(argv).profile.get('name')

        if profile_name != Profile.selected().get('name'):
            self.parser.error("Profile %s is not selected." % profile_name)

        Profile.controller().unselect()
        return EXIT_SUCCESS


COMMAND = ProfileUnselectCommand(
    __name__,
    summary_fmt=("Unselect the selected profile.\n"
                 "Use `profile list` to see all profiles."))
