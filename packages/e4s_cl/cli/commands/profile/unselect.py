from e4s_cl import EXIT_SUCCESS
from e4s_cl.cli import arguments
from e4s_cl.error import ProfileSelectionError
from e4s_cl.model.profile import Profile
from e4s_cl.cli.command import AbstractCommand

class ProfileUnselectCommand(AbstractCommand):
    """``profile unselect`` subcommand."""

    def _construct_parser(self):
        usage = "%s" % self.command
        parser = arguments.get_parser(prog=self.command, usage=usage, description=self.summary)
        parser.add_argument('name', help="Profile name", nargs='?', metavar='<profile_name>', default=None)
        return parser

    def main(self, argv):
        args = self._parse_args(argv)
        profile_ctrl = Profile.controller()

        try:
            selected = profile_ctrl.selected()
        except ProfileSelectionError as sel_err:
            self.parser.error("No profile selected.")

        if args.name:
            if selected['name'] != args.name:
                self.parser.error("Profile {} is not selected.".format(args.name))

        profile_ctrl.unselect()
        return EXIT_SUCCESS


COMMAND = ProfileUnselectCommand(__name__, summary_fmt=("Unselect the selected profile.\n"
                                                      "Use `profile list` to see all profiles."))
