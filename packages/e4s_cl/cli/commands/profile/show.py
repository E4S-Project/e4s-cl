from e4s_cl import EXIT_SUCCESS
from e4s_cl.cli import arguments
from e4s_cl.cli.cli_view import ShowCommand
from e4s_cl.model.profile import Profile


class ProfileShowCommand(ShowCommand):
    def __init__(self):
        super(ProfileShowCommand, self).__init__(Profile, __name__)


COMMAND = ProfileShowCommand()
