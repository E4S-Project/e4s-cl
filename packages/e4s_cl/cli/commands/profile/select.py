"""
Select the profile associated with the name passed as an argument.
The selected profile is internally recorded and will be used implicitly in several commands.
"""

from e4s_cl import EXIT_SUCCESS
from e4s_cl.cli import arguments
from e4s_cl.model.profile import Profile
from e4s_cl.cli.command import AbstractCommand


class ProfileSelectCommand(AbstractCommand):
    """``profile select`` subcommand."""
    def _construct_parser(self):
        usage = f"{self.command} <profile_name>"
        parser = arguments.get_model_identifier(Profile,
                                                prog=self.command,
                                                usage=usage,
                                                description=self.summary)
        return parser

    def main(self, argv):
        profile = self._parse_args(argv).profile
        Profile.controller().select(profile)
        return EXIT_SUCCESS


COMMAND = ProfileSelectCommand(
    __name__,
    summary_fmt=("Select a profile.\n"
                 "Use `profile list` to see all profiles."))
