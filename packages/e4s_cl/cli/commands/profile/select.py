"""
Select a profile to be used as default later.
"""

from e4s_cl import EXIT_SUCCESS
from e4s_cl.cli import arguments
from e4s_cl.model.profile import Profile
from e4s_cl.cli.command import AbstractCommand


class ProfileSelectCommand(AbstractCommand):
    """``profile select`` subcommand."""
    def _construct_parser(self):
        usage = "%s <profile_name>" % self.command
        parser = arguments.get_parser(prog=self.command,
                                      usage=usage,
                                      description=self.summary)
        parser.add_argument('name',
                            help="Profile name",
                            metavar='<profile_name>')
        return parser

    def main(self, argv):
        args = self._parse_args(argv)
        profile_ctrl = Profile.controller()
        name = args.name
        profile = profile_ctrl.one({"name": name})
        if not profile:
            self.parser.error("There is no profile configuration named '%s.'" %
                              name)
        profile_ctrl.select(profile)
        return EXIT_SUCCESS


COMMAND = ProfileSelectCommand(
    __name__,
    summary_fmt=("Select a profile.\n"
                 "Use `profile list` to see all profiles."))
